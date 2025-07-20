language_contexts = {
    'csharp': {
        'conventions': 'PascalCase for methods and properties, camelCase for fields',
        'performance_patterns': [
            'N+1 Query: Database calls inside loops (e.g., GetById() in foreach) - Look for repository.GetById() or similar calls inside foreach/for loops',
            'Multiple enumeration: Calling Count(), Any(), First() multiple times on same IEnumerable - Look for multiple LINQ operations on same variable',
            'Inefficient LINQ: Use of .Where().Count() instead of .Count(predicate) - Look for chained Where().Count() patterns',
            'String concatenation: Using + operator in loops instead of StringBuilder - Look for string += inside loops',
            'Unnecessary boxing/unboxing: Value types being boxed to object unnecessarily',
            'Missing async/await for I/O operations: Synchronous database/file/network calls that should be async',
            'Entity Framework N+1: Loading related entities in loops instead of using Include() or batch loading',
            'IDisposable not disposed: Objects implementing IDisposable not wrapped in using statements',
            'Inefficient collection operations: Using Add() in loops instead of AddRange() or bulk operations'
        ],
        'security_concerns': [
            'SQL injection vulnerabilities',
            'XSS in web applications',
            'Improper input validation',
            'Missing authorization checks'
        ],
        'best_practices': [
            'Proper disposal of IDisposable objects',
            'Async/await patterns',
            'Exception handling specificity',
            'Nullable reference types usage'
        ]
    },
    'javascript': {
        'conventions': 'camelCase for variables/functions',
        'performance_patterns': [
            'DOM queries in loops: document.querySelector/getElementById inside for/while loops - cache DOM references',
            'Memory leaks in closures: Event listeners not removed, timers not cleared, or circular references',
            'Inefficient array operations: Using forEach/map when simple for loop would be faster, or nested loops with O(n²) complexity',
            'Missing debouncing/throttling: Event handlers (scroll, resize, input) without rate limiting',
            'Synchronous operations blocking UI: Long-running synchronous code that should use setTimeout/requestAnimationFrame',
            'Unoptimized event handling: Event listeners added in loops without delegation',
            'Unnecessary re-renders: State updates in loops or missing dependency arrays in useEffect',
            'Memory leaks in React: Missing cleanup in useEffect, not removing event listeners'
        ],
        'security_concerns': [
            'XSS vulnerabilities',
            'CSRF attacks',
            'Client-side validation only',
            'Insecure data storage'
        ],
        'best_practices': [
            'Proper async/await usage',
            'Error handling in promises',
            'Event listener cleanup',
            'Immutable data patterns'
        ]
    },
    'typescript': {
        'conventions': 'camelCase for variables/functions, PascalCase for types/interfaces',
        'performance_patterns': [
            'Unnecessary type assertions',
            'Inefficient array/object operations',
            'Improper use of any',
            'Missing async/await',
            'Synchronous operations blocking UI',
            'Unoptimized change detection in Angular'
        ],
        'security_concerns': [
            'XSS vulnerabilities',
            'CSRF attacks',
            'Client-side validation only',
            'Insecure data storage'
        ],
        'best_practices': [
            'Use type-safe interfaces',
            'Avoid any where possible',
            'Proper error handling',
            'Use readonly and const',
            'Leverage union/intersection types'
        ]
    },
    'react': {
        'conventions': 'PascalCase for components, camelCase for props/state',
        'performance_patterns': [
            'Unnecessary re-renders',
            'Inefficient use of useEffect',
            'Large component trees',
            'Not using React.memo',
            'Inline function definitions in render',
            'Heavy use of state in deeply nested components'
        ],
        'security_concerns': [
            'XSS in dangerouslySetInnerHTML',
            'Insecure data handling in props',
            'Improper input validation',
            'Leaking sensitive data in client logs'
        ],
        'best_practices': [
            'Use functional components',
            'Proper use of hooks',
            'PropTypes or TypeScript for type safety',
            'Component composition over inheritance',
            'Keep components small and focused'
        ]
    },
    'angular': {
        'conventions': 'camelCase for variables/functions, PascalCase for components/services',
        'performance_patterns': [
            'Unoptimized change detection',
            'Inefficient use of ngFor',
            'Memory leaks in subscriptions',
            'Heavy use of two-way binding',
            'Large modules/components',
            'Inefficient DOM manipulation in templates'
        ],
        'security_concerns': [
            'XSS in templates',
            'Insecure use of innerHTML',
            'Improper input validation',
            'Missing authorization checks'
        ],
        'best_practices': [
            'Use OnPush change detection',
            'Unsubscribe from Observables',
            'Use services for business logic',
            'Leverage Angular CLI for structure',
            'Keep templates simple'
        ]
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