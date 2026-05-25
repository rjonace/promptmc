import re

with open("tests/test_cli.py", "r") as f:
    content = f.read()

# For run commands
content = re.sub(
    r'@patch\("promptmc.cli.OpenMCIntegration"\)\ndef test_run_success',
    '@patch("promptmc.cli.OpenMCValidator")\n@patch("promptmc.cli.OpenMCRunner")\ndef test_run_success',
    content
)
content = re.sub(
    r'def test_run_success\(mock_integration_cls, tmp_path\):',
    'def test_run_success(mock_runner_cls, mock_validator_cls, tmp_path):',
    content
)
content = re.sub(
    r'mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = True\n\s+mock_integration.run_simulation.return_value = mock_result\n\s+mock_integration_cls.return_value = mock_integration',
    'mock_runner = MagicMock()\n    mock_runner.run_simulation.return_value = mock_result\n    mock_runner_cls.return_value = mock_runner\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = True\n    mock_validator_cls.return_value = mock_validator',
    content
)

content = re.sub(
    r'@patch\("promptmc.cli.OpenMCIntegration"\)\ndef test_run_simulation_failure',
    '@patch("promptmc.cli.OpenMCValidator")\n@patch("promptmc.cli.OpenMCRunner")\ndef test_run_simulation_failure',
    content
)
content = re.sub(
    r'def test_run_simulation_failure\(mock_integration_cls, tmp_path\):',
    'def test_run_simulation_failure(mock_runner_cls, mock_validator_cls, tmp_path):',
    content
)
content = re.sub(
    r'mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = True\n\s+mock_integration.run_simulation.side_effect = OpenMCExecutionError\("Failed"\)\n\s+mock_integration_cls.return_value = mock_integration',
    'mock_runner = MagicMock()\n    mock_runner.run_simulation.side_effect = OpenMCExecutionError("Failed")\n    mock_runner_cls.return_value = mock_runner\n    mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = True\n    mock_validator_cls.return_value = mock_validator',
    content
)

content = re.sub(
    r'@patch\("promptmc.cli.OpenMCIntegration"\)\ndef test_run_validation_error',
    '@patch("promptmc.cli.OpenMCValidator")\n@patch("promptmc.cli.OpenMCRunner")\ndef test_run_validation_error',
    content
)
content = re.sub(
    r'def test_run_validation_error\(mock_integration_cls, tmp_path\):',
    'def test_run_validation_error(mock_runner_cls, mock_validator_cls, tmp_path):',
    content
)
content = re.sub(
    r'mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.side_effect = OpenMCValidationError\("Invalid"\)\n\s+mock_integration_cls.return_value = mock_integration',
    'mock_validator = MagicMock()\n    mock_validator.validate_input_file.side_effect = OpenMCValidationError("Invalid")\n    mock_validator_cls.return_value = mock_validator',
    content
)

content = re.sub(
    r'@patch\("promptmc.cli.OpenMCIntegration"\)\ndef test_run_not_found_error',
    '@patch("promptmc.cli.OpenMCValidator")\n@patch("promptmc.cli.OpenMCRunner")\ndef test_run_not_found_error',
    content
)
content = re.sub(
    r'def test_run_not_found_error\(mock_integration_cls, tmp_path\):',
    'def test_run_not_found_error(mock_runner_cls, mock_validator_cls, tmp_path):',
    content
)
content = re.sub(
    r'mock_integration = MagicMock\(\)\n\s+mock_integration.validate_input_file.return_value = True\n\s+mock_integration.run_simulation.side_effect = OpenMCNotFoundError\("Not found"\)\n\s+mock_integration_cls.return_value = mock_integration',
    'mock_validator = MagicMock()\n    mock_validator.validate_input_file.return_value = True\n    mock_validator_cls.return_value = mock_validator\n    mock_runner = MagicMock()\n    mock_runner.run_simulation.side_effect = OpenMCNotFoundError("Not found")\n    mock_runner_cls.return_value = mock_runner',
    content
)


# For configure commands
content = re.sub(
    r'@patch\("promptmc.cli.OpenMCIntegration"\)\ndef test_configure',
    '@patch("promptmc.cli.OpenMCRunner")\ndef test_configure',
    content
)
content = re.sub(
    r'mock_integration = MagicMock\(\)\n\s+mock_integration_cls.return_value = mock_integration',
    'mock_runner = MagicMock()\n    mock_integration_cls.return_value = mock_runner',
    content
)
content = content.replace("mock_integration_cls", "mock_runner_cls")
content = content.replace("mock_integration.generate_configuration", "mock_runner.generate_configuration")


# For validate commands
content = re.sub(
    r'@patch\("promptmc.cli.OpenMCIntegration"\)\ndef test_validate',
    '@patch("promptmc.cli.OpenMCValidator")\ndef test_validate',
    content
)
content = content.replace("mock_integration_cls", "mock_validator_cls")
content = content.replace("mock_integration.validate_input_file", "mock_validator.validate_input_file")
content = re.sub(
    r'mock_integration = MagicMock\(\)\n\s+mock_validator_cls.return_value = mock_integration',
    'mock_validator = MagicMock()\n    mock_validator_cls.return_value = mock_validator',
    content
)


# For info commands
content = re.sub(
    r'@patch\("promptmc.cli.OpenMCIntegration"\)\ndef test_info',
    '@patch("promptmc.cli.OpenMCInstaller")\ndef test_info',
    content
)
content = content.replace("mock_integration_cls", "mock_installer_cls")
content = content.replace("mock_integration.check_installation", "mock_installer.check_installation")
content = re.sub(
    r'mock_integration = MagicMock\(\)\n\s+mock_installer_cls.return_value = mock_integration',
    'mock_installer = MagicMock()\n    mock_installer_cls.return_value = mock_installer',
    content
)

content = content.replace("assert 'Unknown template' in result.stdout", "assert 'is not a valid TemplateType' in result.stdout")

with open("tests/test_cli.py", "w") as f:
    f.write(content)
