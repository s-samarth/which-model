"""Unit tests for the deterministic tools: catalog, hardware, costs."""

from pathlib import Path

import pytest

from whichmodel.schemas import (
    ContextNeed,
    Deployment,
    Hardware,
    ModelRow,
    Requirements,
    TaskCategory,
)
from whichmodel.tools import catalog, costs, hardware

SEED_DB = Path(__file__).parent.parent / "data" / "models.db"
SNIPPETS = Path(__file__).parent.parent / "data" / "hardware_snippets.yaml"


@pytest.fixture(scope="module")
def conn():
    c = catalog.connect(SEED_DB)
    yield c
    c.close()


class TestCatalog:
    def test_lookup_by_various_names(self, conn):
        assert catalog.lookup_model(conn, "anthropic/claude-sonnet-5") is not None
        assert catalog.lookup_model(conn, "claude-sonnet-5") is not None
        assert catalog.lookup_model(conn, "qwen3.5:4b").id == "local/qwen3.5-4b"
        assert catalog.lookup_model(conn, "totally-made-up-model-9000") is None

    def test_coding_candidates_ranked_by_agentic_coding(self, conn):
        req = Requirements(task_category=TaskCategory.coding, deployment=Deployment.api)
        cands = catalog.find_candidates(conn, req)
        assert len(cands) >= 3
        assert cands[0].rank_score >= cands[1].rank_score
        assert all(c.available_api for c in cands)

    def test_local_deployment_respects_memory(self, conn):
        req = Requirements(
            task_category=TaskCategory.chat_assistant,
            deployment=Deployment.local,
            hardware=Hardware(ram_gb=16, os="macos"),
        )
        cands = catalog.find_candidates(conn, req)
        assert cands, "16GB Mac should have local options"
        usable = 16 * 0.7
        for c in cands:
            assert c.available_local
            assert c.est_memory_gb is None or c.est_memory_gb <= usable

    def test_budget_filters_expensive_models(self, conn):
        req = Requirements(
            task_category=TaskCategory.chat_assistant,
            deployment=Deployment.api,
            budget_monthly_usd=5.0,
            usage_level="moderate",
        )
        for c in catalog.find_candidates(conn, req):
            assert c.est_monthly_usd is None or c.est_monthly_usd <= 5.0

    def test_image_task_filters_modality(self, conn):
        req = Requirements(
            task_category=TaskCategory.image_understanding, deployment=Deployment.api
        )
        cands = catalog.find_candidates(conn, req)
        assert cands
        assert all("image" in c.input_modalities for c in cands)

    def test_long_context_filter(self, conn):
        req = Requirements(
            task_category=TaskCategory.rag_doc_qa,
            deployment=Deployment.api,
            context_need=ContextNeed.long,
        )
        for c in catalog.find_candidates(conn, req):
            assert c.context_length >= 131_000

    def test_data_age_readable(self, conn):
        age = catalog.data_age(conn)
        assert age and age != "unknown"


class TestCosts:
    def _row(self, prompt=1.0, completion=4.0, free=False):
        return ModelRow(id="x/y", name="y", prompt_usd_per_m=prompt,
                        completion_usd_per_m=completion, is_free=free)

    def test_moderate_usage_math(self):
        # 6M in * $1/M + 2.5M out * $4/M = $16
        assert costs.estimate_monthly_usd(self._row(), "moderate") == 16.0

    def test_free_model_is_zero(self):
        assert costs.estimate_monthly_usd(self._row(free=True), "heavy") == 0.0

    def test_unpriced_returns_none(self):
        assert costs.estimate_monthly_usd(self._row(prompt=None), "light") is None

    def test_inr_conversion(self):
        assert costs.usd_to_inr(10.0, 84.0) == 840
        assert costs.usd_to_inr(None, 84.0) is None


class TestHardware:
    def test_snippet_selection_and_safety(self):
        snips = hardware.load_snippets(SNIPPETS)
        assert set(snips) == {"macos_system", "linux_system", "windows_system"}
        assert hardware.snippet_for_os(SNIPPETS, "linux").os == "linux"
        assert hardware.snippet_for_os(SNIPPETS, None).os == "macos"
        for s in snips.values():  # read-only probes only
            for bad in ("rm ", "sudo", "curl", "wget", "| sh", "> /", ">> "):
                assert bad not in s.command

    def test_parse_mac_output(self):
        out = "      Chip: Apple M2\n      Memory: 16 GB\n15.5\n"
        hw = hardware.parse_probe_output(out)
        assert hw.ram_gb == 16
        assert "Apple M2" in hw.gpu
        assert hw.os == "macos"
        assert hw.usable_memory_gb == 11.2

    def test_parse_linux_nvidia(self):
        out = ("              total        used\nMem:             31          8\n"
               "Linux 6.8.0-41-generic\nNVIDIA GeForce RTX 4070, 12282 MiB\n")
        hw = hardware.parse_probe_output(out)
        assert hw.ram_gb == 32
        assert "4070" in hw.gpu
        assert hw.vram_gb == 12.0
        assert hw.os == "linux"
        assert hw.usable_memory_gb == 12.0

    def test_parse_windows_output(self):
        out = ("TotalPhysicalMemory\n-------------------\n        17179869184\n\n"
               "Name                          AdapterRAM\n"
               "NVIDIA GeForce RTX 3060       12884901888\n")
        hw = hardware.parse_probe_output(out)
        assert hw.ram_gb == 16
        assert "3060" in hw.gpu
        assert hw.vram_gb == 12.0
        assert hw.os == "windows"

    def test_parse_garbage_is_graceful(self):
        hw = hardware.parse_probe_output("i dont know what any of this means")
        assert hw.ram_gb is None and hw.gpu is None
        assert hw.usable_memory_gb is None

    def test_probe_detection(self):
        assert hardware.looks_like_probe_output("Chip: Apple M3\nMemory: 24 GB")
        assert not hardware.looks_like_probe_output("I have a macbook air")
