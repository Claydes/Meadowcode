import io
import tarfile
from types import SimpleNamespace

from apps.judge.services import (
    _build_submission_archive,
    _outputs_equal,
    _read_limited_logs,
    _validate_function_test_case,
)


def test_function_outputs_are_compared_as_json():
    assert _outputs_equal('{"value":1,"items":[2,3]}', '{"items":[2,3],"value":1}')


def test_function_test_case_requires_json_args_array():
    test_case = SimpleNamespace(
        input_data='{"args":"not-a-list"}',
        expected_output="1",
    )

    error = _validate_function_test_case(test_case, 1)

    assert error == "Test case #1 field 'args' must be a JSON array."


def test_function_archive_contains_runner_and_entry_point():
    payload = _build_submission_archive(
        "def add(a, b):\n    return a + b\n",
        '{"args":[2,3]}',
        function_name="add",
    )

    with tarfile.open(fileobj=io.BytesIO(payload), mode="r") as archive:
        names = set(archive.getnames())
        function_name = archive.extractfile("sandbox/function_name.txt").read()

    assert "sandbox/runner.py" in names
    assert function_name == b"add"


def test_docker_logs_are_read_with_a_hard_byte_limit():
    class FakeContainer:
        def logs(self, **kwargs):
            assert kwargs["stream"] is True
            yield b"abc"
            yield b"def"
            raise AssertionError("Reader should stop after the limit is exceeded.")

    payload, exceeded = _read_limited_logs(
        FakeContainer(),
        stdout=True,
        stderr=False,
        limit=5,
    )

    assert payload == b"abcde"
    assert exceeded is True
