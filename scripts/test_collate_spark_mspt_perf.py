from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import collate_spark_mspt_perf as collator


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


SAMPLE_LOG = """[05Apr2026 14:05:15.660] [Server thread/INFO] [net.minecraft.server.MinecraftServer/]: [RabidHobbit: Running function rabidbalance:bench/start]
[05Apr2026 14:05:15.668] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] Running function rabidbalance:bench/start
[05Apr2026 14:05:15.670] [Server thread/INFO] [net.minecraft.server.MinecraftServer/]: [Not Secure] [RabidHobbit] BEGIN Perf Test
[05Apr2026 14:05:15.676] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [RabidHobbit] BEGIN Perf Test
[05Apr2026 14:05:16.451] [Server thread/INFO] [net.minecraft.server.MinecraftServer/]: [Not Secure] [RabidHobbit] Capture Now
[05Apr2026 14:05:16.457] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [RabidHobbit] Capture Now
[05Apr2026 14:05:16.457] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [Click to run spark]
[05Apr2026 14:05:18.024] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] TPS from last 5s, 10s, 1m, 5m, 15m:
[05Apr2026 14:05:18.026] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  19.97, 19.98, 20.0, 20.0, 20.0
[05Apr2026 14:05:18.026] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]
[05Apr2026 14:05:18.028] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] Tick durations (min/med/95%ile/max ms) from last 10s, 1m:
[05Apr2026 14:05:18.028] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  0.3/11.8/37.2/793.6;  0.3/10.6/38.8/793.6
[05Apr2026 14:05:18.028] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]
[05Apr2026 14:05:18.029] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] CPU usage from last 10s, 1m, 15m:
[05Apr2026 14:05:18.029] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  33%, 21%, 6%  (system)
[05Apr2026 14:05:18.029] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  29%, 17%, 5%  (process)
[05Apr2026 14:05:25.681] [Server thread/INFO] [net.minecraft.server.MinecraftServer/]: [Not Secure] [Server] Capture Now
[05Apr2026 14:05:25.702] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [Server] Capture Now
[05Apr2026 14:05:25.702] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [Click to run spark]
[05Apr2026 14:05:26.548] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] TPS from last 5s, 10s, 1m, 5m, 15m:
[05Apr2026 14:05:26.549] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  19.98, 19.99, *20.0, *20.0, *20.0
[05Apr2026 14:05:26.549] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]
[05Apr2026 14:05:26.549] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] Tick durations (min/med/95%ile/max ms) from last 10s, 1m:
[05Apr2026 14:05:26.551] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  0.3/9.6/49.9/810.8;  0.3/10.7/49.5/810.8
[05Apr2026 14:05:26.551] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]
[05Apr2026 14:05:26.551] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] CPU usage from last 10s, 1m, 15m:
[05Apr2026 14:05:26.551] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  27%, 24%, 6%  (system)
[05Apr2026 14:05:26.551] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  25%, 20%, 5%  (process)
[05Apr2026 14:05:35.732] [Server thread/INFO] [net.minecraft.server.MinecraftServer/]: [Not Secure] [Server] Capture Now
[05Apr2026 14:05:35.747] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [Server] Capture Now
[05Apr2026 14:05:35.747] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [Click to run spark]
[05Apr2026 14:05:36.522] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] TPS from last 5s, 10s, 1m, 5m, 15m:
[05Apr2026 14:05:36.522] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  *20.0, *20.0, *20.0, *20.0, *20.0
[05Apr2026 14:05:36.522] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]
[05Apr2026 14:05:36.524] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] Tick durations (min/med/95%ile/max ms) from last 10s, 1m:
[05Apr2026 14:05:36.524] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  2.8/11.0/39.4/422.4;  0.3/10.7/49.3/810.8
[05Apr2026 14:05:36.524] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]
[05Apr2026 14:05:36.524] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1] CPU usage from last 10s, 1m, 15m:
[05Apr2026 14:05:36.524] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  26%, 26%, 7%  (system)
[05Apr2026 14:05:36.524] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [\u26a1]  24%, 23%, 5%  (process)
[05Apr2026 14:06:15.632] [Server thread/INFO] [net.minecraft.server.MinecraftServer/]: [Not Secure] [Server] END Perf Test
[05Apr2026 14:06:15.645] [Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]: [System] [CHAT] [Server] END Perf Test
"""


class CollateSparkMsptPerfTests(unittest.TestCase):
    def test_cli_scans_only_top_level_logs_by_default_and_overwrites_shared_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            logs_dir = root / "logs"
            logs_dir.mkdir()
            nested_dir = logs_dir / "nested"
            nested_dir.mkdir()
            first_log_path = logs_dir / "spark-session-a.log"
            second_log_path = logs_dir / "spark-session-b.log"
            nested_log_path = nested_dir / "spark-session-c.log"
            first_log_path.write_text(SAMPLE_LOG, encoding="utf-8")
            second_log_path.write_text(SAMPLE_LOG, encoding="utf-8")
            nested_log_path.write_text(SAMPLE_LOG, encoding="utf-8")

            first_exit_code = collator.main([str(logs_dir)])
            second_exit_code = collator.main([str(logs_dir)])

            self.assertEqual(first_exit_code, 0)
            self.assertEqual(second_exit_code, 0)
            output_path = logs_dir / "spark_perf_captures.csv"
            self.assertTrue(output_path.exists())

            header = read_csv_header(output_path)
            self.assertEqual(
                header[:14],
                [
                    "source_log",
                    "session_start_timestamp",
                    "session_index",
                    "capture_index",
                    "mspt_10s_min",
                    "mspt_10s_median",
                    "mspt_10s_p95",
                    "mspt_10s_max",
                    "capture_timestamp",
                    "mspt_1m_min",
                    "mspt_1m_median",
                    "mspt_1m_p95",
                    "mspt_1m_max",
                    "parsed_at",
                ],
            )

            rows = read_csv_rows(output_path)
            self.assertEqual(len(rows), 6)
            self.assertEqual({row["source_log"] for row in rows}, {"spark-session-a.log", "spark-session-b.log"})

            first_row = rows[0]
            self.assertEqual(first_row["source_log"], "spark-session-a.log")
            self.assertTrue(first_row["parsed_at"])
            self.assertEqual(first_row["session_index"], "1")
            self.assertEqual(first_row["session_actor"], "RabidHobbit")
            self.assertEqual(first_row["capture_index"], "1")
            self.assertEqual(first_row["capture_actor"], "RabidHobbit")
            self.assertEqual(first_row["capture_timestamp"], "2026-04-05T14:05:16.451")
            self.assertEqual(first_row["spark_timestamp"], "2026-04-05T14:05:18.024")
            self.assertEqual(first_row["seconds_since_session_start"], "0.781")
            self.assertEqual(first_row["seconds_from_capture_to_spark"], "1.573")
            self.assertEqual(first_row["tps_5s"], "19.97")
            self.assertEqual(first_row["tps_1m_starred"], "false")
            self.assertEqual(first_row["mspt_10s_median"], "11.8")
            self.assertEqual(first_row["cpu_process_1m_pct"], "17")

            second_row = rows[1]
            self.assertEqual(second_row["capture_index"], "2")
            self.assertEqual(second_row["capture_actor"], "Server")
            self.assertEqual(second_row["tps_1m_starred"], "true")
            self.assertEqual(second_row["tps_15m_starred"], "true")
            self.assertEqual(second_row["mspt_1m_p95"], "49.5")
            self.assertEqual(second_row["cpu_system_10s_pct"], "27")

            third_row = rows[2]
            self.assertEqual(third_row["parsed_at"], first_row["parsed_at"])
            self.assertEqual(third_row["capture_index"], "3")
            self.assertEqual(third_row["tps_5s_starred"], "true")
            self.assertEqual(third_row["tps_15m_starred"], "true")
            self.assertEqual(third_row["mspt_10s_min"], "2.8")
            self.assertEqual(third_row["cpu_process_1m_pct"], "23")

            fourth_row = rows[3]
            self.assertEqual(fourth_row["source_log"], "spark-session-b.log")
            self.assertEqual(fourth_row["parsed_at"], first_row["parsed_at"])
            self.assertEqual(fourth_row["capture_index"], "1")
            self.assertEqual(fourth_row["capture_actor"], "RabidHobbit")

    def test_cli_includes_nested_logs_with_recursive_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            logs_dir = root / "logs"
            logs_dir.mkdir()
            nested_dir = logs_dir / "nested"
            nested_dir.mkdir()

            (logs_dir / "spark-session-a.log").write_text(SAMPLE_LOG, encoding="utf-8")
            (logs_dir / "spark-session-b.log").write_text(SAMPLE_LOG, encoding="utf-8")
            (nested_dir / "spark-session-c.log").write_text(SAMPLE_LOG, encoding="utf-8")

            exit_code = collator.main([str(logs_dir), "--recursive"])

            self.assertEqual(exit_code, 0)
            rows = read_csv_rows(logs_dir / "spark_perf_captures.csv")
            self.assertEqual(len(rows), 9)
            self.assertEqual(
                {row["source_log"] for row in rows},
                {"spark-session-a.log", "spark-session-b.log", "spark-session-c.log"},
            )


if __name__ == "__main__":
    unittest.main()
