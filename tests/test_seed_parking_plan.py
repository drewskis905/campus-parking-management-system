"""Run with: python -m unittest discover -s tests -p test_seed_parking_plan.py"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import algorithm_version2 as algorithm
import walk_time
from database import database as db
from database import seed_parking_plan as seed


class ParkingPlanSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_database = db.DATABASE
        db.DATABASE = str(Path(self.temp.name) / "parking.db")
        db.create_tables()
        walk_time._MATRIX_CACHE.clear()
        conn = db.get_connection()
        try:
            conn.executemany(
                "INSERT INTO lots(name, lat, lng, capacity) VALUES (?, ?, ?, ?)",
                [(lot["name"], lot["lat"], lot["lng"], lot["capacity"])
                 for lot in walk_time.load_lots()],
            )
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        db.DATABASE = self.old_database
        walk_time._MATRIX_CACHE.clear()
        self.temp.cleanup()

    def add_students(self, count=1):
        conn = db.get_connection()
        try:
            for user_id in range(1, count + 1):
                conn.execute(
                    "INSERT INTO users VALUES (?, 'Test', 'Student', ?, 'unused')",
                    (user_id, f"student{user_id}@test.com"),
                )
                conn.executemany(
                    "INSERT INTO schedules(user_id, class_name, building, day, start_time, end_time) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [(user_id, "CECS 100", "Engineering/Computer Sciences (ECS)",
                      "Monday/Wednesday", "07:00", "08:00"),
                     (user_id, "CECS 200", "Engineering 2",
                      "Monday/Wednesday", "12:00", "13:00")],
                )
            conn.commit()
        finally:
            conn.close()

    def run_seed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return seed.seed_parking_plan()

    def test_1000_users_real_ranking_storage_cache_and_rerun(self):
        self.add_students(1000)
        recommendations_seen = []

        def route_response(*args, **kwargs):
            body = kwargs["json"]
            return Mock(status_code=200, json=lambda: {
                "durations": [[60] * len(body["destinations"])
                              for _ in body["sources"]]
            })

        def choose(options):
            recommendations_seen.append(options)
            return options[(len(recommendations_seen) - 1) % len(options)]

        with patch.object(walk_time.requests, "post", side_effect=route_response) as post:
            with patch.object(seed.random, "choice", side_effect=choose):
                self.assertEqual(self.run_seed(), 2000)
            self.assertEqual(post.call_count, 2)
            self.assertEqual(self.run_seed(), 0)
            self.assertEqual(post.call_count, 2)

        conn = db.get_connection()
        try:
            plans = conn.execute(
                "SELECT user_id, lot, day, start_time, end_time FROM parking_plans ORDER BY id"
            ).fetchall()
        finally:
            conn.close()
        self.assertEqual(len(plans), 2000)
        self.assertEqual(len({(row[0], row[2]) for row in plans}), 2000)
        for index, row in enumerate(plans):
            self.assertIn(row[2], {"Monday", "Wednesday"})
            self.assertEqual(row[3:], ("07:00", "13:00"))
            self.assertEqual(len(recommendations_seen[index]), 3)
            self.assertEqual(row[1], recommendations_seen[index][index % 3]["lot"])
        # Later rankings must observe plans committed for earlier users.
        self.assertTrue(any(option["planned_occupied"] > 0
                            for options in recommendations_seen[2:] for option in options))

    def test_existing_combined_days_empty_user_and_weekend(self):
        self.add_students(2)
        conn = db.get_connection()
        try:
            conn.execute("DELETE FROM schedules WHERE user_id = 2")
            conn.execute("UPDATE schedules SET day = 'Monday/Wednesday/Saturday' WHERE user_id = 1")
            conn.commit()
        finally:
            conn.close()
        self.assertTrue(db.add_parking_plan(1, "G3", "Monday/Wednesday", "07:00", "13:00")["success"])
        with patch.object(seed, "get_lot_recommendations", return_value=[{"lot": "G3"}]) as recommend:
            self.assertEqual(self.run_seed(), 1)
            self.assertEqual(recommend.call_args.kwargs["day"], "Saturday")
            self.assertEqual(recommend.call_args.kwargs["exclude_student_id"], 1)
        self.assertEqual(len(db.get_user_parking_plans(1)), 2)
        self.assertEqual(db.get_user_parking_plans(2), [])

    def test_routing_failure_can_resume_and_empty_routes_are_skipped(self):
        self.add_students()
        with patch.object(seed, "get_lot_recommendations", side_effect=[[{"lot": "G3"}], None]):
            with self.assertRaisesRegex(RuntimeError, "1 new plans were saved"):
                self.run_seed()
        self.assertEqual(len(db.get_user_parking_plans(1)), 1)
        with patch.object(seed, "get_lot_recommendations", return_value=[]):
            self.assertEqual(self.run_seed(), 0)
        with patch.object(seed, "get_lot_recommendations", return_value=[{"lot": "G3"}]):
            self.assertEqual(self.run_seed(), 1)
        self.assertEqual(len(db.get_user_parking_plans(1)), 2)

    def test_matrix_failures_are_not_cached_and_return_values_are_independent(self):
        failed = Mock(status_code=429, text="Rate limited")
        success = Mock(status_code=200, json=lambda: {"durations": [[120]]})
        with patch.object(walk_time.requests, "post", side_effect=[failed, success]) as post:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(walk_time.get_walk_time_matrix([(1, 2)], [(3, 4)]))
            result = walk_time.get_walk_time_matrix([(1, 2)], [(3, 4)])
            result[0][0] = 999
            self.assertEqual(walk_time.get_walk_time_matrix([(1, 2)], [(3, 4)]), [[2]])
            self.assertEqual(post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
