---
author: Computer System
category: development
created: '2025-06-18T20:25:36.821115'
description: Template for code review tasks
name: Code Review
variables:
- COMPONENT_NAME
- RECOMMENDATIONS
- AUTHOR
- REVIEW_FINDINGS
- PURPOSE
- FILE_LIST
version: '1.0'
---

# Code Review: {{COMPONENT_NAME}}

## Review Scope
- **Component**: {{COMPONENT_NAME}}
- **Files**: {{FILE_LIST}}
- **Author**: {{AUTHOR}}
- **Purpose**: {{PURPOSE}}

## Review Checklist
### Code Quality
- [ ] Follows project coding standards
- [ ] Functions are well-named and documented
- [ ] Code is DRY (Don't Repeat Yourself)
- [ ] Complex logic is commented
- [ ] Error handling is appropriate

### Security
- [ ] Input validation implemented
- [ ] No hardcoded secrets or credentials
- [ ] SQL injection prevention
- [ ] XSS protection where applicable
- [ ] Authentication/authorization correct

### Performance
- [ ] No obvious performance bottlenecks
- [ ] Database queries optimized
- [ ] Caching used appropriately
- [ ] Memory usage reasonable

### Testing
- [ ] Unit tests cover new functionality
- [ ] Integration tests where needed
- [ ] Edge cases tested
- [ ] Mock objects used appropriately

## Findings
{{REVIEW_FINDINGS}}

## Recommendations
{{RECOMMENDATIONS}}

## Approval Status
- [ ] Approved
- [ ] Approved with minor changes
- [ ] Requires changes
- [ ] Rejected