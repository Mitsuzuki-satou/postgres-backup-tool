# Contributing to PostgreSQL Advanced Backup & Restore Tool

Thank you for your interest in contributing to this project! We welcome contributions from everyone, whether you're fixing a bug, adding a feature, or improving documentation.

## 🤝 How to Contribute

### 1. Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/postgres-backup-tool.git
   cd postgres-backup-tool
   ```
3. **Create a branch** for your contribution:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-description
   ```

### 2. Development Setup

**Prerequisites:**
- Bash 4.0+
- PostgreSQL client tools (`psql`, `pg_dump`, `pg_restore`)
- Git
- A text editor or IDE

**Test Environment Setup:**
```bash
# Install PostgreSQL client tools (if not already installed)
# Ubuntu/Debian
sudo apt install postgresql-client

# Arch Linux  
sudo pacman -S postgresql

# macOS
brew install postgresql
```

### 3. Making Changes

**Code Style Guidelines:**
- Use 4 spaces for indentation (no tabs)
- Keep lines under 100 characters when possible
- Use meaningful variable and function names
- Add comments for complex logic
- Follow existing naming conventions

**Function Naming:**
- Use lowercase with underscores: `function_name()`
- Use descriptive names: `monitor_backup_progress()` not `progress()`
- Prefix utility functions with their purpose: `print_color()`, `log()`

**Variable Naming:**
- Use uppercase for constants: `readonly CONFIG_FILE="..."`
- Use lowercase for local variables: `local backup_file="..."`
- Use descriptive names: `estimated_size` not `size`

**Error Handling:**
- Always check command exit codes
- Use meaningful error messages
- Include cleanup procedures for failed operations
- Log errors with timestamps

### 4. Testing Your Changes

**Manual Testing:**
```bash
# Make the script executable
chmod +x postgres-backup-restore.sh

# Test the interactive menu
./postgres-backup-restore.sh

# Test specific functions (if you added command-line options)
./postgres-backup-restore.sh --test-connections
```

**Test Checklist:**
- [ ] Script starts without errors
- [ ] Interactive menu displays correctly
- [ ] Configuration can be saved and loaded
- [ ] Connection testing works
- [ ] Progress bars display properly
- [ ] Error handling works as expected
- [ ] Cleanup procedures execute on failure
- [ ] Logs are created correctly

### 5. Code Review Process

**Before Submitting:**
- Test your changes thoroughly
- Check for any debug output or temporary code
- Ensure no sensitive information is hardcoded
- Verify error handling works properly
- Update documentation if needed

**Commit Message Format:**
```
Type: Brief description (50 chars max)

Longer explanation of what this commit does and why.
Include any breaking changes or important notes.

- Additional bullet points if needed
- Reference issues: Fixes #123, Closes #456
```

**Commit Types:**
- `Add:` New features
- `Fix:` Bug fixes
- `Update:` Changes to existing features
- `Remove:` Removing features/code
- `Docs:` Documentation changes
- `Style:` Code style changes (formatting, etc.)
- `Refactor:` Code refactoring
- `Test:` Adding or updating tests

### 6. Submitting Your Contribution

1. **Push your changes:**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request:**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template

**Pull Request Template:**
```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] I have tested my changes locally
- [ ] I have added/updated tests as needed
- [ ] All existing tests pass

## Screenshots (if applicable)
Add screenshots to help explain your changes.

## Additional Notes
Any additional information about the changes.
```

## 🐛 Bug Reports

**Before Submitting a Bug Report:**
- Check if the issue already exists
- Test with the latest version
- Try to reproduce the issue consistently

**Bug Report Template:**
```markdown
**Describe the Bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. Select option '...'
3. Enter data '...'
4. See error

**Expected Behavior**
What you expected to happen.

**Screenshots**
Add screenshots if applicable.

**Environment:**
- OS: [e.g. Ubuntu 20.04, Arch Linux, macOS]
- Bash version: [e.g. 5.0]
- PostgreSQL version: [e.g. 13.4]
- Script version: [e.g. v2.0]

**Additional Context**
Add any other context about the problem.

**Log Output**
Include relevant log output from ~/.postgres_backup_logs/
```

## 💡 Feature Requests

**Feature Request Template:**
```markdown
**Feature Description**
A clear description of what you want to happen.

**Use Case**
Describe the use case and why this feature would be useful.

**Proposed Solution**
If you have ideas on how to implement this, describe them here.

**Alternatives Considered**
Any alternative solutions you've considered.

**Additional Context**
Add any other context or screenshots about the feature.
```

## 🎯 Areas for Contribution

### High Priority
- **Cloud Storage Integration**: AWS S3, Google Cloud, Azure Blob
- **Database Monitoring**: Real-time connection status, performance metrics
- **Backup Scheduling**: Cron integration, automated backups
- **Configuration Validation**: Input validation, connection verification
- **Multi-database Support**: Backup multiple databases in one operation

### Medium Priority  
- **Backup Encryption**: GPG encryption for sensitive data
- **Backup Verification**: Integrity checks, restore testing
- **Email Notifications**: Success/failure notifications
- **Web Interface**: Simple web UI for remote management
- **Docker Support**: Containerized version

### Low Priority
- **Backup Rotation**: Automatic old backup cleanup
- **Compression Algorithms**: Support for different compression methods
- **Progress API**: JSON output for integration with other tools
- **Internationalization**: Multi-language support
- **Theme Customization**: Color scheme options

## 📝 Documentation Contributions

**Types of Documentation Needed:**
- Installation guides for different operating systems
- Configuration examples for common scenarios  
- Video tutorials for complex operations
- API documentation for advanced usage
- Troubleshooting guides for common issues

**Documentation Style:**
- Use clear, simple language
- Include code examples
- Add screenshots for UI elements
- Test all commands and examples
- Keep formatting consistent

## 🧪 Testing Guidelines

**Manual Testing Areas:**
- Connection handling (success/failure scenarios)
- Progress bar accuracy during operations
- Configuration persistence across runs
- Error handling and cleanup procedures
- Different PostgreSQL versions compatibility
- Various operating system compatibility

**Test Scenarios:**
```bash
# Connection testing
./postgres-backup-restore.sh
# Select option 4, test with invalid credentials

# Backup testing
# Test with small database (< 1GB)
# Test with large database (> 5GB)
# Test with many tables (> 100)
# Test network interruption scenarios

# Restore testing  
# Test SQL format restore
# Test compressed format restore
# Test directory format restore
# Test database name conflicts
```

## 🏆 Recognition

Contributors will be recognized in several ways:
- Added to the README.md contributors section
- Mentioned in release notes for significant contributions
- GitHub contributor badge on the repository
- Optional: Added to CONTRIBUTORS.md with brief bio (if desired)

## 📞 Getting Help

**Communication Channels:**
- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Request Comments**: For code-specific questions

**Response Times:**
- Issues: We aim to respond within 48 hours
- Pull Requests: Initial review within 1 week
- Discussions: Best effort, usually within a few days

## 📄 Code of Conduct

### Our Standards

**Positive behaviors:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other contributors

**Unacceptable behaviors:**
- Use of sexualized language or imagery
- Trolling, insulting/derogatory comments
- Public or private harassment
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Project maintainers have the right to remove, edit, or reject comments, commits, code, and other contributions that don't align with this Code of Conduct.

## 🙏 Thank You

Every contribution, no matter how small, helps make this tool better for everyone. Thank you for taking the time to contribute!

---

*This contributing guide is inspired by best practices from successful open-source projects and will evolve as our community grows.*
