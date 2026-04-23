# Agents and Knowledge Base

This document tracks agents, knowledge, and memory for the Congressional Trade Watcher project.

## AI Agents

### Primary Agent: Code Assistant
- **Purpose**: General coding assistance and implementation
- **Capabilities**: Python development, testing, documentation
- **Memory**: Session-based, project context aware
- **Tools**: Code generation, file editing, terminal commands

### Specialized Agents

#### Documentation Agent
- **Purpose**: Maintain and update project documentation
- **Capabilities**: README updates, manual writing, changelog management
- **Knowledge Base**: Project structure, user guides, API documentation

#### Testing Agent
- **Purpose**: Ensure code quality and reliability
- **Capabilities**: Unit test creation, test execution, coverage analysis
- **Focus Areas**: Core functionality, edge cases, integration testing

#### Deployment Agent
- **Purpose**: Handle deployment and infrastructure
- **Capabilities**: Docker, CI/CD, environment setup
- **Knowledge**: Cron scheduling, server deployment, monitoring

## Knowledge Areas

### Technical Knowledge
- **Python 3.11+**: Async programming, type hints, standard library
- **HTTP APIs**: RESTful design, authentication, rate limiting
- **Data Processing**: JSON handling, deduplication, normalization
- **Error Handling**: Retries, logging, graceful degradation

### Domain Knowledge
- **Congressional Trading**: STOCK Act requirements, disclosure timing
- **Financial Data**: Stock symbols, trade types, regulatory compliance
- **API Integration**: FMP endpoints, data formats, authentication

### Project Knowledge
- **Architecture**: Modular design, separation of concerns
- **Configuration**: Environment variables, config files
- **Deployment**: Cron scheduling, local execution
- **Maintenance**: Updates, backups, troubleshooting

## Memory and Context

### Session Memory
- Current development tasks
- Recent changes and decisions
- User preferences and requirements

### Repository Memory
- Project conventions and patterns
- Verified practices and solutions
- Historical decisions and rationale

### External Knowledge
- Financial regulations and compliance
- API documentation and changes
- Community best practices

## Communication Protocols

### Agent Communication
- Use clear, structured messages
- Provide context and reasoning
- Document decisions and changes

### Knowledge Sharing
- Update documentation for new learnings
- Share solutions and patterns
- Maintain changelog for changes

### User Interaction
- Clear explanations of actions
- Progress updates for long tasks
- Error handling with helpful messages

## Maintenance

### Regular Updates
- Review and update knowledge base monthly
- Archive outdated information
- Document new patterns and solutions

### Quality Assurance
- Validate knowledge accuracy
- Test agent capabilities regularly
- Update documentation for changes

### Collaboration
- Share knowledge across agents
- Document inter-agent dependencies
- Maintain consistent terminology