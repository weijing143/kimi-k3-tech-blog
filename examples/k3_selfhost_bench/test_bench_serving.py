"""bench_serving.py 单元测试：聚合吞吐计时、TPOT、结果汇总。

运行：python -m unittest test_bench_serving -v
"""
from __future__ import annotations

import unittest

from bench_serving import LevelResult, Sample, make_prompt


class TestSample(unittest.TestCase):
    def test_tpot(self):
        s = Sample(ttft=1.0, e2e=3.0, output_tokens=11)
        self.assertAlmostEqual(s.tpot, 0.2)

    def test_tpot_none_without_stream(self):
        self.assertIsNone(Sample(e2e=2.0, output_tokens=10).tpot)
        self.assertIsNone(Sample(ttft=1.0, e2e=2.0, output_tokens=1).tpot)


class TestAggregateThroughput(unittest.TestCase):
    def test_wall_time_used_not_max_e2e(self):
        """请求排队时聚合吞吐必须用整批墙钟时间，而非单请求最大 e2e。"""
        # 4 个请求并发 2：每个 e2e=1s，两批共 2s 墙钟
        r = LevelResult(concurrency=2, wall_s=2.0)
        r.samples = [Sample(ttft=0.1, e2e=1.0, output_tokens=10) for _ in range(4)]
        summary = r.summary()
        # 总输出 40 tok / 2s 墙钟 = 20 tok/s；旧的 max-e2e 口径会算成 40 tok/s（高估一倍）
        self.assertEqual(summary["agg_output_tps"], 20.0)
        self.assertEqual(summary["wall_s"], 2.0)

    def test_errors_counted(self):
        r = LevelResult(concurrency=1, wall_s=5.0)
        r.samples = [Sample(e2e=1.0, output_tokens=5),
                     Sample(e2e=0.5, error="TimeoutError: boom")]
        summary = r.summary()
        self.assertEqual(summary["ok"], 1)
        self.assertEqual(summary["errors"], 1)


class TestMakePrompt(unittest.TestCase):
    def test_reproducible_and_sized(self):
        p1, p2 = make_prompt(1000), make_prompt(1000)
        self.assertEqual(p1, p2)  # 内容固定才能跨并发级别对比
        self.assertEqual(len(p1), 3500)  # 1000 token × 3.5 字符


if __name__ == "__main__":
    unittest.main()
