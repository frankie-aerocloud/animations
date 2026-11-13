import math
import unittest

from studio.core.motion import ease_in_expo, ease_in_out, ease_out_expo, heading, point_along, polyline_length, unwrap


class MotionTests(unittest.TestCase):
    def test_easing_endpoints(self):
        for fn in (ease_in_out, ease_out_expo, ease_in_expo):
            self.assertAlmostEqual(fn(0.0), 0.0, places=3)
            self.assertAlmostEqual(fn(1.0), 1.0, places=3)
            self.assertTrue(0.0 <= fn(0.5) <= 1.0)

    def test_polyline_sampling(self):
        path = [(0, 0), (3, 0), (3, 4)]
        self.assertEqual(polyline_length(path), 7.0)
        self.assertEqual(point_along(path, 0.0), (0.0, 0.0))
        self.assertEqual(point_along(path, 3.0), (3.0, 0.0))
        self.assertEqual(point_along(path, 5.0), (3.0, 2.0))
        self.assertEqual(point_along(path, 99.0), (3.0, 4.0))

    def test_heading_points_local_y_towards_target(self):
        self.assertAlmostEqual(heading((0, 0), (0, 1)), 0.0)
        self.assertAlmostEqual(heading((0, 0), (-1, 0)), math.pi / 2)
        self.assertAlmostEqual(heading((0, 0), (1, 0)), -math.pi / 2)

    def test_unwrap_takes_short_way_round(self):
        self.assertAlmostEqual(unwrap(3.0, -3.0), -3.0 + math.tau)
        self.assertAlmostEqual(unwrap(0.0, 0.5), 0.5)


if __name__ == "__main__":
    unittest.main()
