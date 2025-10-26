import * as parser from '@babel/parser'
// @ts-types="npm:@types/babel__traverse"
import traverse from '@babel/traverse'
import { Hono } from 'hono'

/* flag location: /flag */

Object.defineProperties(globalThis, Object.getOwnPropertyDescriptors(Math))

function checkSafetyRegex(code: string) {
  const whitelist = /^[a-zA-Z0-9_+\-*/%() ]+$/
  if (!whitelist.test(code)) {
    throw new Error('Bad Code (whitelist)')
  }
  const blacklist =
    /(eval|Function|__proto__|constructor|prototype|window|document|import|require|process|globalThis|self|global|this|module|exports|fetch|new|confirm|alert|prompt|%[0-9a-f]{2})/i
  if (blacklist.test(code)) {
    throw new Error('Bad Code (blacklist)')
  }
}

function checkSafeAST(code: string) {
  const ast = parser.parse(code, {
    sourceType: 'script'
  })
  traverse.default(ast, {
    enter(path) {
      // NO strings!
      if (path.isStringLiteral()) {
        throw new Error('Bad Code (isStringLiteral)')
      }
      // NO member expressions!
      if (path.isThisExpression()) {
        throw new Error('Bad Code (isThisExpression)')
      }
      if (path.isMemberExpression()) {
        throw new Error('Bad Code (isMemberExpression)')
      }
      if (path.isOptionalMemberExpression()) {
        throw new Error('Bad Code (isOptionalMemberExpression)')
      }
      if (path.isCallExpression()) {
        const callee = path.get('callee')
        if (callee.isMemberExpression() || callee.isOptionalMemberExpression()) {
          throw new Error('Bad Code (isCallExpression)')
        }
      }
      // NO comments!
      if (path.node.leadingComments || path.node.innerComments || path.node.trailingComments) {
        throw new Error('Bad Code (comments)')
      }
      // NO Objects!
      if (path.isObjectExpression()) {
        throw new Error('Bad Code (isObjectExpression)')
      }
      if (path.isObjectPattern()) {
        throw new Error('Bad Code (isObjectPattern)')
      }
      // NO Arrays!
      if (path.isArrayExpression()) {
        throw new Error('Bad Code (isArrayExpression)')
      }
      if (path.isArrayPattern()) {
        throw new Error('Bad Code (isArrayPattern)')
      }
      // NO destructuring!
      if (path.isRestElement()) {
        throw new Error('Bad Code (isRestElement)')
      }
      if (path.isSpreadElement()) {
        throw new Error('Bad Code (isSpreadElement)')
      }
      // NO functions!
      if (path.isFunctionDeclaration()) {
        throw new Error('Bad Code (isFunctionDeclaration)')
      }
      if (path.isFunctionExpression()) {
        throw new Error('Bad Code (isFunctionExpression)')
      }
      if (path.isArrowFunctionExpression()) {
        throw new Error('Bad Code (isArrowFunctionExpression)')
      }
      // NO classes!
      if (path.isClassDeclaration()) {
        throw new Error('Bad Code (isClassDeclaration)')
      }
      if (path.isClassExpression()) {
        throw new Error('Bad Code (isClassExpression)')
      }
      // NO new!
      if (path.isNewExpression()) {
        throw new Error('Bad Code (isNewExpression)')
      }
      // NO eval!
      if (path.isIdentifier({ name: 'eval' })) {
        throw new Error('Bad Code (eval)')
      }
      if (path.isIdentifier({ name: 'Function' })) {
        throw new Error('Bad Code (Function)')
      }
      // NO variables!
      if (path.isIdentifier()) {
        const name = path.node.name
        if (!(name in globalThis)) {
          throw new Error('Bad Code (variable)')
        }
      }
    }
  })
}

function checkSafe(code: string) {
  checkSafetyRegex(code)
  checkSafeAST(code)
}

const app = new Hono()

app.get('/', (c) => {
  // #region HTML UI
  return c.html(
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>CalcaaS - Calculator as a Service</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .fade-in {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
      </head>
      <body class="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 min-h-screen">
        <div class="container mx-auto px-4 py-4 max-w-3xl">
          {/* Header */}
          <div class="text-center mb-6 fade-in">
            <h1 class="text-4xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-2">
              CalcaaS
            </h1>
            <p class="text-gray-600 text-base">
              Calculator as a Service - Secure Expression Evaluation
            </p>
          </div>

          {/* Main Calculator Card */}
          <div class="bg-white rounded-xl shadow-xl p-5 mb-5 fade-in">
            <div class="mb-4">
              <label for="expression" class="block text-sm font-semibold text-gray-700 mb-1.5">
                Enter Mathematical Expression
              </label>
              <input
                type="text"
                id="expression"
                class="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all duration-200 font-mono text-base"
                placeholder="e.g., 2 + 2 * 3"
              />
            </div>

            <button
              type="button"
              onclick="evaluateExpression()"
              class="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold py-3 px-5 rounded-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
            >
              Calculate
            </button>

            {/* Result Display */}
            <div id="result-container" class="mt-4 hidden">
              <div class="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-lg p-3">
                <p class="text-xs font-semibold text-green-700 mb-0.5">Result:</p>
                <p id="result" class="text-xl font-bold text-green-900 font-mono"></p>
              </div>
            </div>

            {/* Error Display */}
            <div id="error-container" class="mt-4 hidden">
              <div class="bg-gradient-to-r from-red-50 to-pink-50 border-2 border-red-200 rounded-lg p-3">
                <p id="error" class="text-sm text-red-900 font-mono"></p>
              </div>
            </div>
          </div>

          {/* Examples */}
          <div class="bg-white rounded-xl shadow-lg p-4 fade-in">
            <h3 class="text-base font-bold text-gray-800 mb-3">Example Expressions</h3>
            <div class="grid md:grid-cols-3 gap-2">
              <button
                type="button"
                onclick="setExpression('2 + 2 * 3')"
                class="bg-gray-50 hover:bg-indigo-50 border-2 border-gray-200 hover:border-indigo-300 rounded-lg p-2 text-left transition-all duration-200"
              >
                <code class="text-xs font-mono text-gray-700">2 + 2 * 3</code>
              </button>
              <button
                type="button"
                onclick="setExpression('(10 + 5) * 2')"
                class="bg-gray-50 hover:bg-indigo-50 border-2 border-gray-200 hover:border-indigo-300 rounded-lg p-2 text-left transition-all duration-200"
              >
                <code class="text-xs font-mono text-gray-700">(10 + 5) * 2</code>
              </button>
              <button
                type="button"
                onclick="setExpression('abs(-100) + sqrt(16)')"
                class="bg-gray-50 hover:bg-indigo-50 border-2 border-gray-200 hover:border-indigo-300 rounded-lg p-2 text-left transition-all duration-200"
              >
                <code class="text-xs font-mono text-gray-700">abs(-100) + sqrt(16)</code>
              </button>
            </div>
          </div>

          {/* Footer */}
          <div class="text-center mt-5">
            <button
              type="button"
              onclick="downloadSource()"
              class="inline-flex items-center gap-2 bg-gradient-to-r from-gray-700 to-gray-900 hover:from-gray-800 hover:to-black text-white font-semibold py-2 px-4 rounded-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 mb-3"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                  clip-rule="evenodd"
                />
              </svg>
              Download Source Code
            </button>
            <p class="text-gray-500 text-sm">
              Powered by secure expression evaluation with AST validation
            </p>
          </div>
        </div>

        <script
          dangerouslySetInnerHTML={{
            __html: `
        function setExpression(expr) {
          document.getElementById('expression').value = expr;
        }

        async function evaluateExpression() {
          const expression = document.getElementById('expression').value.trim();
          const resultContainer = document.getElementById('result-container');
          const errorContainer = document.getElementById('error-container');
          const resultElement = document.getElementById('result');
          const errorElement = document.getElementById('error');

          // Hide previous results
          resultContainer.classList.add('hidden');
          errorContainer.classList.add('hidden');

          if (!expression) {
            errorElement.textContent = 'Please enter an expression';
            errorContainer.classList.remove('hidden');
            return;
          }

          try {
            const response = await fetch('/eval', {
              method: 'POST',
              headers: {
                'Content-Type': 'text/plain',
              },
              body: expression
            });

            const data = await response.json();

            if (response.ok) {
              resultElement.textContent = data.result;
              resultContainer.classList.remove('hidden');
            } else {
              errorElement.textContent = data.error || 'An error occurred';
              errorContainer.classList.remove('hidden');
            }
          } catch (error) {
            errorElement.textContent = 'Network error: ' + error.message;
            errorContainer.classList.remove('hidden');
          }
        }

        // Allow Enter key to submit
        document.getElementById('expression').addEventListener('keydown', function(e) {
          if (e.key === 'Enter') {
            e.preventDefault();
            evaluateExpression();
          }
        });

        async function downloadSource() {
          try {
            const response = await fetch('/source');
            if (!response.ok) {
              throw new Error('Failed to fetch source code');
            }
            const sourceCode = await response.text();
            
            // Create a blob and download link
            const blob = new Blob([sourceCode], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'app.tsx';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
          } catch (error) {
            alert('Error downloading source code: ' + error.message);
          }
        }
      `
          }}
        ></script>
      </body>
    </html>
  )
  // #endregion
})
app.post('/eval', async (c) => {
  const code = await c.req.text()
  console.group('Incoming request:')
  console.group('Code:')
  console.log(code)
  console.groupEnd()
  try {
    checkSafe(code)
    const result = eval(code)
    if (JSON.stringify(result)?.length > 64) {
      console.log('Result: too long')
      return c.json({ error: 'Result too long' }, 400)
    } else {
      console.log('Result:', result)
      return c.json({ result })
    }
  } catch (e) {
    console.log(e)
    return c.json({ error: '' + e }, 400)
  } finally {
    console.groupEnd()
  }
})
app.get('/source', async (c) => {
  // #region Source Code Route
  const source = await Deno.readTextFile(new URL(import.meta.url))
  const minified = source
    .replace(/\/\/ #region[\s\S]*?\/\/ #endregion/gm, '/* <irrelevant code removed> */')
    .replace(/\/\/.*$/gm, '')
    .replace(/^\s*[\r\n]/gm, '')
  return c.body(minified)
  // #endregion
})

Deno.serve(app.fetch)
