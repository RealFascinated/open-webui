/**
 * Builds a self-contained HTML page that renders a React/JSX component.
 *
 * How it works:
 *  - React 18, ReactDOM, and @babel/standalone are loaded from unpkg at runtime.
 *  - Tailwind CSS is included for styling (no import needed).
 *  - Additional libraries are conditionally loaded based on import statements
 *    detected in the source: recharts, lodash, mathjs, d3, papaparse.
 *  - A `require()` shim maps CommonJS imports (produced by Babel's
 *    transform-modules-commonjs plugin) to the globally-loaded UMD bundles.
 *  - Babel transpiles the JSX/TSX via a `<script type="text/babel">` block.
 *  - The default export is auto-rendered to #root after transpilation.
 *
 * NOT available: lucide-react (ESM-only, no UMD bundle), shadcn/ui, axios, next.js,
 * framer-motion, react-motion. Use CSS transitions/keyframes for animations.
 */
import {
	type ArtifactCanvasTheme,
	artifactCanvasStyleBlock,
	artifactCanvasHtmlAttrs,
	artifactCanvasTailwindDarkScript
} from './artifact-theme';

export function buildReactHtml(
	jsxCode: string,
	canvasTheme: ArtifactCanvasTheme = 'light'
): string {
	// Prevent </script> in user code from breaking the wrapping HTML page.
	const safeCode = jsxCode.replace(/<\/(script)/gi, '<\\/$1');

	const needsRecharts =
		/from\s+['"]recharts['"]|require\(['"]recharts['"]\)/.test(jsxCode);
	const needsLodash =
		/from\s+['"]lodash['"]|require\(['"]lodash['"]\)|from\s+['"]lodash\//.test(jsxCode);
	const needsMathjs =
		/from\s+['"]mathjs['"]|require\(['"]mathjs['"]\)/.test(jsxCode);
	const needsD3 =
		/from\s+['"]d3['"]|require\(['"]d3['"]\)|from\s+['"]d3\//.test(jsxCode);
	const needsPapaparse =
		/from\s+['"]papaparse['"]|require\(['"]papaparse['"]\)/.test(jsxCode);

	const conditionalScripts = [
		needsRecharts
			? '<script src="https://unpkg.com/recharts/umd/Recharts.js"></script>'
			: '',
		needsLodash   ? '<script src="https://unpkg.com/lodash/lodash.js"></script>'           : '',
		needsMathjs   ? '<script src="https://unpkg.com/mathjs/lib/browser/math.js"></script>' : '',
		needsD3       ? '<script src="https://unpkg.com/d3/dist/d3.min.js"></script>'           : '',
		needsPapaparse ? '<script src="https://unpkg.com/papaparse/papaparse.min.js"></script>' : ''
	]
		.filter(Boolean)
		.join('\n');

	return `<!DOCTYPE html>
<html lang="en" ${artifactCanvasHtmlAttrs(canvasTheme)}>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://unpkg.com/react@18/umd/react.development.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
${conditionalScripts}
${artifactCanvasStyleBlock(canvasTheme)}
${canvasTheme === 'dark' ? artifactCanvasTailwindDarkScript() : ''}
<style>
  *, *::before, *::after { box-sizing: border-box; }
</style>
</head>
<body>
<div id="root"></div>
<script>
  function __reportArtifactError(kind, message) {
    try {
      window.parent.postMessage({
        _owsArtifactError: true,
        kind: kind,
        message: String(message || '')
      }, '*');
    } catch (e) {}
  }
  window.addEventListener('error', function(e) {
    var root = document.getElementById('root');
    var msg = (e.error && e.error.message) || e.message || 'Unknown error';
    if (root && root.childNodes.length === 0) {
      root.innerHTML =
        '<div style="padding:1rem 1.25rem;font-family:monospace;color:#b91c1c;' +
        'background:#fee2e2;border-radius:8px;margin:1rem;font-size:13px;white-space:pre-wrap">' +
        '<strong>Compile error:</strong> ' + msg.replace(/</g, '&lt;') + '</div>';
    }
    __reportArtifactError('compile', msg);
  });
</script>
<script>
  /* ── JSX runtime shim (Babel automatic runtime → React.createElement) ── */
  var __jsxRuntime = {
    Fragment: React.Fragment,
    jsx: function(type, props, key) {
      if (key !== undefined) {
        props = Object.assign({}, props, { key: key });
      }
      return React.createElement(type, props);
    },
    jsxs: function(type, props, key) {
      if (key !== undefined) {
        props = Object.assign({}, props, { key: key });
      }
      return React.createElement(type, props);
    },
    jsxDEV: function(type, props, key) {
      if (key !== undefined) {
        props = Object.assign({}, props, { key: key });
      }
      return React.createElement(type, props);
    }
  };

  /* ── CommonJS shim: maps require() to UMD globals ── */
  var __registry = {
    'react':                    React,
    'react/jsx-runtime':        __jsxRuntime,
    'react/jsx-dev-runtime':    __jsxRuntime,
    'react-dom':                ReactDOM,
    'react-dom/client':   ReactDOM,
    ${needsRecharts   ? "'recharts':   typeof Recharts   !== 'undefined' ? Recharts   : {}," : ''}
    ${needsLodash     ? "'lodash':     typeof _         !== 'undefined' ? _           : {}," : ''}
    ${needsMathjs     ? "'mathjs':     typeof math      !== 'undefined' ? math        : {}," : ''}
    ${needsD3         ? "'d3':         typeof d3        !== 'undefined' ? d3          : {}," : ''}
    ${needsPapaparse  ? "'papaparse':  typeof Papa      !== 'undefined' ? Papa        : {}," : ''}
  };
  window.require = function(mod) {
    if (__registry[mod]) return __registry[mod];
    /* strip sub-paths (e.g. lodash/debounce) and retry */
    var base = mod.split('/')[0];
    if (__registry[base]) return __registry[base];
    console.warn('[React artifact] Module not bundled: ' + mod + ' — returning {}');
    return {};
  };
  window.exports = {};
  window.module  = { exports: window.exports };
${'<'}/script>
<script type="text/babel" data-presets="react,typescript" data-plugins="transform-modules-commonjs">
${safeCode}

/* ── Auto-render ── */
;(function __autoRender() {
  var comp =
    (typeof module !== 'undefined' && module.exports && module.exports['default']) ||
    (typeof exports !== 'undefined' && exports['default']) ||
    (typeof App !== 'undefined' && App) ||
    (typeof Component !== 'undefined' && Component) ||
    (typeof Default !== 'undefined' && Default);

  if (!comp) {
    document.getElementById('root').innerHTML =
      '<div style="padding:1rem 1.25rem;font-family:monospace;color:#b91c1c;' +
      'background:#fee2e2;border-radius:8px;margin:1rem;font-size:13px">' +
      '<strong>No default export found.</strong><br/>' +
      'Add <code style="background:#fca5a5;padding:2px 4px;border-radius:3px">export default function App() { ... }</code> ' +
      'to render your component.</div>';
    __reportArtifactError('export', 'No default export found');
    return;
  }

  try {
    var root = ReactDOM.createRoot(document.getElementById('root'));
    root.render(React.createElement(comp));
  } catch(e) {
    document.getElementById('root').innerHTML =
      '<div style="padding:1rem 1.25rem;font-family:monospace;color:#b91c1c;' +
      'background:#fee2e2;border-radius:8px;margin:1rem;font-size:13px">' +
      '<strong>Render error:</strong> ' + e.message + '</div>';
    __reportArtifactError('render', e.message);
  }
})();
${'<'}/script>
</body>
</html>`;
}
