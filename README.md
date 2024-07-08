# CLI Validation Tool

CLI Validation Tool is simple tool to validate the syntax correctness of CLI commands.

## How to use

```python
import asyncio
from cli_validator import CLIValidator

# Create a new validator
validator = CLIValidator()

# validate a CLI command using the validator
result = asyncio.run(validator.validate_command('az webapp create -g resourceGroupTest -n nameTest -p planTest'))
assert result.is_valid
```

Please note that all methods in `CLIValidator` are async. Please use them in asyncio Runtime.
