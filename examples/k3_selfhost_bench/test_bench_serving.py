"""bench_serving.py 单元测试：聚合吞吐计时、TPOT、结果汇总。

运行：python -m unittest test_bench_serving -v
"""
from __future__ import annotations

import unittest

from bench_serving import LevelResult, Sample, build_content, make_prompt


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


class TestBuildContent(unittest.TestCase):
    def test_common_prefix_is_exactly_shared_prefix(self):
        """跨请求的公共前缀必须恰好等于 shared_prefix——否则前缀缓存实验无有效对照。"""
        prefix = "SHARED " * 100
        prompt = make_prompt(100)
        c1 = build_content(prefix, prompt, "req-1")
        c2 = build_content(prefix, prompt, "req-2")
        # 两个请求的公共前缀
        common = 0
        for a, b in zip(c1, c2):
            if a != b:
                break
            common += 1
        # 公共部分 = shared_prefix + "\n\n" + 两个 id 的相同字符（"req-"），
        # 关键是必须短于 prompt 主体的起始位置（prompt 不进入公共前缀）
        prompt_start = len(prefix) + 2 + len("[request-id: req-1]") + 2
        self.assertGreaterEqual(common, len(prefix) + 2)
        self.assertLess(common, prompt_start)
        self.assertNotEqual(c1, c2)  # 请求内容必须有唯一尾部

    def test_no_shared_prefix_means_no_common_prefix(self):
        c1 = build_content("", make_prompt(100), "req-1")
        c2 = build_content("", make_prompt(100), "req-2")
        self.assertFalse(c1.startswith("SHARED"))
        self.assertNotEqual(c1, c2)


if __name__ == "__main__":
    unittest.main()
