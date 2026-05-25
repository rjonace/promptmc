import re

with open("src/promptmc/cli.py", "r") as f:
    cli_content = f.read()

# Update imports in cli.py
cli_content = cli_content.replace(
    "from promptmc.openmc_integration import ExecutionMode, OpenMCIntegration",
    "from promptmc.openmc_integration import ExecutionMode, OpenMCInstaller, OpenMCRunner, OpenMCValidator"
)

# In run()
cli_content = cli_content.replace(
    "integration = OpenMCIntegration(execution_mode=execution_mode)",
    "runner = OpenMCRunner(execution_mode=execution_mode)\n        validator = OpenMCValidator()"
)
cli_content = cli_content.replace("integration.validate_input_file", "validator.validate_input_file")
cli_content = cli_content.replace("integration.run_simulation", "runner.run_simulation")

# In configure()
cli_content = cli_content.replace(
    "integration = OpenMCIntegration()",
    "runner = OpenMCRunner()"
)
cli_content = cli_content.replace("integration.generate_configuration", "runner.generate_configuration")

# In validate()
cli_content = cli_content.replace(
    "integration = OpenMCIntegration()",
    "validator = OpenMCValidator()"
)

# In info()
cli_content = cli_content.replace(
    "integration = OpenMCIntegration()",
    "installer = OpenMCInstaller()"
)
cli_content = cli_content.replace("integration.check_installation", "installer.check_installation")

with open("src/promptmc/cli.py", "w") as f:
    f.write(cli_content)

with open("src/promptmc/batch.py", "r") as f:
    batch_content = f.read()

batch_content = batch_content.replace(
    "from promptmc.openmc_integration import OpenMCIntegration",
    "from promptmc.openmc_integration import OpenMCRunner"
)
batch_content = batch_content.replace("integration = OpenMCIntegration()", "runner = OpenMCRunner()")
batch_content = batch_content.replace("integration.run_simulation", "runner.run_simulation")

with open("src/promptmc/batch.py", "w") as f:
    f.write(batch_content)
