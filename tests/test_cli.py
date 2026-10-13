from typer.testing import CliRunner

from pipeline.cli import app
from pipeline.run import main as run_main

runner = CliRunner()


def test_demo_end_to_end(tmp_path):
    work = tmp_path / "w"
    res = runner.invoke(app, ["demo", "--workdir", str(work)], env={"COLUMNS": "100"})
    assert res.exit_code == 0, res.output
    out = res.output
    for s in ("1/6", "2/6", "3/6", "4/6", "5/6", "6/6", "모의 추출기", "LLM 아님", "6/6", "[확인 필요]"):
        assert s in out
    assert (work / "report.md").exists() and (work / "report.html").exists()
    assert (work / "out" / "review_queue.csv").exists()

    q = runner.invoke(app, ["queue", "--workdir", str(work)], env={"COLUMNS": "120"})
    assert q.exit_code == 0 and "CT-10" in q.output

    ev = runner.invoke(app, ["evaluate", "--results", str(work / "out" / "results.jsonl"),
                             "--gold", str(work / "samples" / "gold"), "--out", str(tmp_path / "r.md")])
    assert ev.exit_code == 0 and "결함 검출 6/6" in ev.output


def test_run_command_and_queue_empty(tmp_path, samples):
    res = runner.invoke(app, ["run", "--docs", str(samples / "docs"), "--out", str(tmp_path / "o"), "--simulate"],
                        env={"COLUMNS": "160"})
    assert res.exit_code == 0, res.output
    assert "IV-05" in res.output and "공급자 오류" in res.output
    empty = runner.invoke(app, ["queue", "--workdir", str(tmp_path / "none")])
    assert "비어 있습니다" in empty.output


def test_missing_key_exits_2(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    res = runner.invoke(app, ["demo", "--workdir", str(tmp_path), "--provider", "gemini"])
    assert res.exit_code == 2 and "GEMINI_API_KEY" in res.output
    res = runner.invoke(app, ["run", "--provider", "nope"])
    assert res.exit_code == 2


def test_generate_command(tmp_path):
    from docgen.fonts import FontNotFoundError, find_korean_font

    try:
        find_korean_font()
    except FontNotFoundError:
        return
    res = runner.invoke(app, ["generate", "--out", str(tmp_path / "g")])
    assert res.exit_code == 0 and "30건" in res.output


def test_python_m_pipeline_run_offline(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert run_main(["--offline", "--workdir", str(tmp_path), "--simulate-provider-errors"]) == 0
    out = capsys.readouterr().out
    assert "모의 추출기" in out and "확인 대기열 9건" in out
    assert (tmp_path / "report.md").exists()
    assert run_main(["--provider", "gemini", "--workdir", str(tmp_path)]) == 2
