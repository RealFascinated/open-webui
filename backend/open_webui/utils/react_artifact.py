"""Build self-contained HTML pages that render React/JSX components (artifact runtime).

Keep in sync with src/lib/utils/react-artifact.ts — that file is the canonical reference.
"""


def build_react_html(jsx_code: str) -> str:
    safe_code = jsx_code.replace('</script', r'<\/script')

    needs_recharts = "from 'recharts'" in jsx_code or 'from "recharts"' in jsx_code or "require('recharts')" in jsx_code
    needs_lodash = "from 'lodash'" in jsx_code or 'from "lodash"' in jsx_code or "require('lodash')" in jsx_code or "from 'lodash/" in jsx_code
    needs_mathjs = "from 'mathjs'" in jsx_code or 'from "mathjs"' in jsx_code or "require('mathjs')" in jsx_code
    needs_d3 = "from 'd3'" in jsx_code or 'from "d3"' in jsx_code or "require('d3')" in jsx_code or "from 'd3/" in jsx_code
    needs_papaparse = "from 'papaparse'" in jsx_code or 'from "papaparse"' in jsx_code or "require('papaparse')" in jsx_code

    conditional_scripts = '\n'.join(
        s
        for s in [
            '<script src="https://unpkg.com/recharts/umd/Recharts.js"></script>' if needs_recharts else '',
            '<script src="https://unpkg.com/lodash/lodash.js"></script>' if needs_lodash else '',
            '<script src="https://unpkg.com/mathjs/lib/browser/math.js"></script>' if needs_mathjs else '',
            '<script src="https://unpkg.com/d3/dist/d3.min.js"></script>' if needs_d3 else '',
            '<script src="https://unpkg.com/papaparse/papaparse.min.js"></script>' if needs_papaparse else '',
        ]
        if s
    )

    registry_lines = [
        "'react': React,",
        "'react/jsx-runtime': __jsxRuntime,",
        "'react/jsx-dev-runtime': __jsxRuntime,",
        "'react-dom': ReactDOM,",
        "'react-dom/client': ReactDOM,",
    ]
    if needs_recharts:
        registry_lines.append("'recharts': typeof Recharts !== 'undefined' ? Recharts : {},")
    if needs_lodash:
        registry_lines.append("'lodash': typeof _ !== 'undefined' ? _ : {},")
    if needs_mathjs:
        registry_lines.append("'mathjs': typeof math !== 'undefined' ? math : {},")
    if needs_d3:
        registry_lines.append("'d3': typeof d3 !== 'undefined' ? d3 : {},")
    if needs_papaparse:
        registry_lines.append("'papaparse': typeof Papa !== 'undefined' ? Papa : {},")

    registry = '\n    '.join(registry_lines)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://unpkg.com/react@18/umd/react.development.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
{conditional_scripts}
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
</style>
</head>
<body>
<div id="root"></div>
<script>
  function __reportArtifactError(kind, message) {{
    try {{
      window.parent.postMessage({{
        _owsArtifactError: true,
        kind: kind,
        message: String(message || '')
      }}, '*');
    }} catch (e) {{}}
  }}
  window.addEventListener('error', function(e) {{
    var root = document.getElementById('root');
    var msg = (e.error && e.error.message) || e.message || 'Unknown error';
    if (root && root.childNodes.length === 0) {{
      root.innerHTML =
        '<div style="padding:1rem 1.25rem;font-family:monospace;color:#b91c1c;' +
        'background:#fee2e2;border-radius:8px;margin:1rem;font-size:13px;white-space:pre-wrap">' +
        '<strong>Compile error:</strong> ' + msg.replace(/</g, '&lt;') + '</div>';
    }}
    __reportArtifactError('compile', msg);
  }});
</script>
<script>
  var __jsxRuntime = {{
    Fragment: React.Fragment,
    jsx: function(type, props, key) {{
      if (key !== undefined) {{
        props = Object.assign({{}}, props, {{ key: key }});
      }}
      return React.createElement(type, props);
    }},
    jsxs: function(type, props, key) {{
      if (key !== undefined) {{
        props = Object.assign({{}}, props, {{ key: key }});
      }}
      return React.createElement(type, props);
    }},
    jsxDEV: function(type, props, key) {{
      if (key !== undefined) {{
        props = Object.assign({{}}, props, {{ key: key }});
      }}
      return React.createElement(type, props);
    }}
  }};

  var __registry = {{
    {registry}
  }};
  window.require = function(mod) {{
    if (__registry[mod]) return __registry[mod];
    var base = mod.split('/')[0];
    if (__registry[base]) return __registry[base];
    console.warn('[React artifact] Module not bundled: ' + mod);
    return {{}};
  }};
  window.exports = {{}};
  window.module = {{ exports: window.exports }};
</script>
<script type="text/babel" data-presets="react,typescript" data-plugins="transform-modules-commonjs">
{safe_code}

;(function __autoRender() {{
  var comp =
    (typeof module !== 'undefined' && module.exports && module.exports['default']) ||
    (typeof exports !== 'undefined' && exports['default']) ||
    (typeof App !== 'undefined' && App) ||
    (typeof Component !== 'undefined' && Component) ||
    (typeof Default !== 'undefined' && Default);

  if (!comp) {{
    document.getElementById('root').innerHTML =
      '<div style="padding:1rem 1.25rem;font-family:monospace;color:#b91c1c;background:#fee2e2;border-radius:8px;margin:1rem;font-size:13px">' +
      '<strong>No default export found.</strong><br/>' +
      'Add <code style="background:#fca5a5;padding:2px 4px;border-radius:3px">export default function App() {{ ... }}</code> ' +
      'to render your component.</div>';
    __reportArtifactError('export', 'No default export found');
    return;
  }}

  try {{
    var root = ReactDOM.createRoot(document.getElementById('root'));
    root.render(React.createElement(comp));
  }} catch(e) {{
    document.getElementById('root').innerHTML =
      '<div style="padding:1rem 1.25rem;font-family:monospace;color:#b91c1c;background:#fee2e2;border-radius:8px;margin:1rem;font-size:13px">' +
      '<strong>Render error:</strong> ' + e.message + '</div>';
    __reportArtifactError('render', e.message);
  }}
}})();
</script>
</body>
</html>"""
