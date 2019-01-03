import os


def test_parallel_live(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            envlist = a, b
            [testenv]
            commands=python -c "import sys; print(sys.executable)"
        """
        },
    )
    result = cmd("--parallel", "all", "--parallel-live")
    assert result.ret == 0, "{}{}{}".format(result.err, os.linesep, result.out)


def test_parallel(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            envlist = a, b
            [testenv]
            commands=python -c "import sys; print(sys.executable)"
        """
        },
    )
    result = cmd("--parallel", "all")
    assert result.ret == 0, "{}{}{}".format(result.err, os.linesep, result.out)


def test_parallel_error_report(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            envlist = a
            [testenv]
            commands=python -c "import sys, os; sys.stderr.write(str(12345) + os.linesep);\
             raise SystemExit(17)"
        """
        },
    )
    result = cmd("-p", "all")
    msg = "{}{}{}".format(result.err, os.linesep, result.out)
    assert result.ret == 1, msg
    # we print output
    assert "(exited with code 17)" in result.out, msg
    assert "Failed a under process " in result.out, msg

    assert any(line for line in result.outlines if line == "12345")

    # single summary at end
    summary_lines = [j for j, l in enumerate(result.outlines) if " summary " in l]
    assert len(summary_lines) == 1, msg

    assert result.outlines[summary_lines[0] + 1 :] == ["ERROR:   a: 1"]
