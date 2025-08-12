language_contexts = {
    'csharp': {
        'conventions': 'PascalCase methods, camelCase fields',
        'performance_patterns': ['N+1 queries', 'Memory leaks', 'LINQ optimization', 'String concatenation in loops', 'Missing async/await'],
        'security_concerns': ['Input validation', 'Authorization', 'SQL injection', 'XSS'],
        'best_practices': ['Async/await', 'IDisposable', 'Exception handling', 'Nullable types']
    },
    'javascript': {
        'conventions': 'camelCase variables/functions',
        'performance_patterns': ['DOM queries in loops', 'Memory leaks', 'Event cleanup', 'Inefficient loops', 'Missing debouncing'],
        'security_concerns': ['XSS', 'CSRF', 'Input validation', 'Insecure storage'],
        'best_practices': ['Async/await', 'Error handling', 'Event cleanup', 'Immutable patterns']
    },
    'typescript': {
        'conventions': 'camelCase variables/functions, PascalCase types/interfaces',
        'performance_patterns': ['Unnecessary type assertions', 'Inefficient operations', 'Improper use of any', 'Missing async/await'],
        'security_concerns': ['XSS', 'CSRF', 'Input validation', 'Insecure storage'],
        'best_practices': ['Type-safe interfaces', 'Avoid any', 'Error handling', 'Readonly types']
    },
    'react': {
        'conventions': 'PascalCase components, camelCase props/state',
        'performance_patterns': ['Unnecessary re-renders', 'Inefficient useEffect', 'Large components', 'Missing React.memo'],
        'security_concerns': ['XSS in dangerouslySetInnerHTML', 'Insecure props', 'Input validation', 'Data leakage'],
        'best_practices': ['Functional components', 'Proper hooks', 'Type safety', 'Small components']
    },
    'angular': {
        'conventions': 'camelCase variables/functions, PascalCase components/services',
        'performance_patterns': ['Unoptimized change detection', 'Inefficient ngFor', 'Memory leaks', 'Heavy two-way binding'],
        'security_concerns': ['XSS in templates', 'Insecure innerHTML', 'Input validation', 'Authorization'],
        'best_practices': ['OnPush change detection', 'Unsubscribe from Observables', 'Service usage', 'Simple templates']
    }
}

def get_language_context(code_type: str) -> str:
    ctx = language_contexts.get(code_type.lower())
    if not ctx:
        return ''
    return (
        f"- Conventions: {ctx['conventions']}\n"
        f"- Performance patterns: {', '.join(ctx['performance_patterns'])}\n"
        f"- Security concerns: {', '.join(ctx['security_concerns'])}\n"
        f"- Best practices: {', '.join(ctx['best_practices'])}"
    )