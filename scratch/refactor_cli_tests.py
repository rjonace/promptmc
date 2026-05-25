import re

with open("tests/test_cli.py", "r") as f:
    content = f.read()

# Replace run_success
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_run_success\(mock_integration_cls, tmp_path\):\n\s+mock_result = MagicMock\(\)\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = True\n\s+mock_integration.run_simulation.return_value = mock_result\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCRunner")\n@patch("promptmc.cli.OpenMCValidator")\ndef test_run_success(mock_validator_cls, mock_runner_cls, tmp_path):\n    mock_result = MagicMock()\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = True\n    mock_validator_cls.return_value = mock_validator\n    mock_runner = MagicMock()\n    mock_runner.run_simulation.return_value = mock_result\n    mock_runner_cls.return_value = mock_runner',
    content
)

# Replace run_simulation_failure
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_run_simulation_failure\(mock_integration_cls, tmp_path\):\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = True\n\s+mock_integration.run_simulation.side_effect = OpenMCExecutionError\(\n\s+"Failed"\n\s+\)\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCRunner")\n@patch("promptmc.cli.OpenMCValidator")\ndef test_run_simulation_failure(mock_validator_cls, mock_runner_cls, tmp_path):\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = True\n    mock_validator_cls.return_value = mock_validator\n    mock_runner = MagicMock()\n    mock_runner.run_simulation.side_effect = OpenMCExecutionError("Failed")\n    mock_runner_cls.return_value = mock_runner',
    content
)

# Replace run_validation_error
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_run_validation_error\(mock_integration_cls, tmp_path\):\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.side_effect = OpenMCValidationError\(\n\s+"Invalid"\n\s+\)\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCValidator")\ndef test_run_validation_error(mock_validator_cls, tmp_path):\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.side_effect = OpenMCValidationError("Invalid")\n    mock_validator_cls.return_value = mock_validator',
    content
)

# Replace run_not_found_error
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_run_not_found_error\(mock_integration_cls, tmp_path\):\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = True\n\s+mock_integration.run_simulation.side_effect = OpenMCNotFoundError\(\n\s+"Not found"\n\s+\)\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCRunner")\n@patch("promptmc.cli.OpenMCValidator")\ndef test_run_not_found_error(mock_validator_cls, mock_runner_cls, tmp_path):\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = True\n    mock_validator_cls.return_value = mock_validator\n    mock_runner = MagicMock()\n    mock_runner.run_simulation.side_effect = OpenMCNotFoundError("Not found")\n    mock_runner_cls.return_value = mock_runner',
    content
)

# Replace configure_success
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_configure_success\(mock_integration_cls\):\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.generate_configuration.return_value = Path\(\n\s+"openmc_config\.xml"\n\s+\)\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCRunner")\ndef test_configure_success(mock_runner_cls):\n    mock_runner = MagicMock()\n    mock_runner.generate_configuration.return_value = Path("openmc_config.xml")\n    mock_runner_cls.return_value = mock_runner',
    content
)

# Replace configure_error
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_configure_error\(mock_integration_cls\):\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.generate_configuration.side_effect = RuntimeError\(\n\s+"disk full"\n\s+\)\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCRunner")\ndef test_configure_error(mock_runner_cls):\n    mock_runner = MagicMock()\n    mock_runner.generate_configuration.side_effect = RuntimeError("disk full")\n    mock_runner_cls.return_value = mock_runner',
    content
)

# Replace validate_success
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_validate_success\(mock_integration_cls\):\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = True\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCValidator")\ndef test_validate_success(mock_validator_cls):\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = True\n    mock_validator_cls.return_value = mock_validator',
    content
)

# Replace validate_fail
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_validate_fail\(mock_integration_cls\):\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = False\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCValidator")\ndef test_validate_fail(mock_validator_cls):\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = False\n    mock_validator_cls.return_value = mock_validator',
    content
)

# Replace validate_with_schema
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_validate_with_schema\(mock_integration_cls\):\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = True\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCValidator")\ndef test_validate_with_schema(mock_validator_cls):\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = True\n    mock_validator_cls.return_value = mock_validator',
    content
)

# Replace info_success
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_info_success\(mock_integration_cls\):\n\s+mock_info = MagicMock\(\)\n\s+mock_info.version = "0\.14\.0"\n\s+mock_info.python_available = True\n\s+mock_info.subprocess_available = True\n\s+mock_info.executable_path = "/usr/local/bin/openmc"\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.check_installation.return_value = mock_info\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCInstaller")\ndef test_info_success(mock_installer_cls):\n    mock_info = MagicMock()\n    mock_info.version = "0.14.0"\n    mock_info.python_available = True\n    mock_info.subprocess_available = True\n    mock_info.executable_path = "/usr/local/bin/openmc"\n    mock_installer = MagicMock()\n    mock_installer.check_installation.return_value = mock_info\n    mock_installer_cls.return_value = mock_installer',
    content
)

# Replace info_not_found
content = re.sub(
    r'@patch\("promptmc\.cli\.OpenMCIntegration"\)\ndef test_info_not_found\(mock_integration_cls\):\n\s+from promptmc.openmc_integration import OpenMCNotFoundError\n\n\s+mock_integration = MagicMock\(\)\n\s+mock_integration.check_installation.side_effect = OpenMCNotFoundError\(\n\s+"not found"\n\s+\)\n\s+mock_integration_cls.return_value = mock_integration',
    '@patch("promptmc.cli.OpenMCInstaller")\ndef test_info_not_found(mock_installer_cls):\n    from promptmc.openmc_integration import OpenMCNotFoundError\n\n    mock_installer = MagicMock()\n    mock_installer.check_installation.side_effect = OpenMCNotFoundError("not found")\n    mock_installer_cls.return_value = mock_installer',
    content
)

content = content.replace("assert 'Unknown template' in result.stdout", "assert 'is not a valid TemplateType' in result.stdout")

with open("tests/test_cli.py", "w") as f:
    f.write(content)
