import { readFileSync, readdirSync } from 'node:fs'

export function providerIconLicenses() {
  const root = new URL('../src/assets/provider-icons/', import.meta.url)
  const files = [
    'ATTRIBUTION.md',
    ...readdirSync(new URL('licenses/', root)).map(name => `licenses/${name}`),
  ]

  return {
    name: 'provider-icon-licenses',
    generateBundle() {
      for (const file of files) {
        this.emitFile({
          type: 'asset',
          fileName: `assets/provider-icons/${file}`,
          source: readFileSync(new URL(file, root)),
        })
      }
    },
  }
}
