VALIDATION_MARKER = "VALIDATION_PASSED"


def classify_run(exit_status: str, command_outputs: list[str], error: str | None) -> str:
    if error:
        return "exception"
    if exit_status != "Submitted":
        return "not_submitted"
    if any(VALIDATION_MARKER in output for output in command_outputs):
        return "success"
    return "validation_failed"
