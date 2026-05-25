import re

with open("src/promptmc/errors.py", "r") as f:
    content = f.read()

# Add tenacity import
content = content.replace("from typing import Any, Callable", "from typing import Any, Callable\n\nimport tenacity")

# Remove RetryPolicy and retry implementation
new_retry_code = """
def default_retry() -> Callable[..., Any]:
    \"\"\"Default retry decorator using tenacity.\"\"\"
    return tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type((OSError, TimeoutError, ExecutionError)),
        reraise=True,
    )
"""

# Replace everything from @dataclass class RetryPolicy: to the end of the file
content = re.sub(r'@dataclass\nclass RetryPolicy:.*', new_retry_code, content, flags=re.DOTALL)

with open("src/promptmc/errors.py", "w") as f:
    f.write(content.strip() + "\n")

# Remove tests from test_errors.py
with open("tests/test_errors.py", "r") as f:
    test_content = f.read()

test_content = re.sub(r'def test_retry_policy_compute_delay\(\):.*', '', test_content, flags=re.DOTALL)

with open("tests/test_errors.py", "w") as f:
    f.write(test_content.strip() + "\n")

