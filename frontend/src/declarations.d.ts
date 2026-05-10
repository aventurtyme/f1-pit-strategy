// src/declarations.d.ts
// Tells TypeScript that *.module.css imports are valid
// and return a record of class name strings.

declare module '*.module.css' {
  const classes: Record<string, string>
  export default classes
}

declare module '*.css' {
  const css: string
  export default css
}

declare module '*.css' {}