import { expect, test } from '@playwright/test'

test('la navegación superior cambia de vista sin dejar la página en blanco', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  const nav = page.getByRole('navigation', { name: 'Secciones principales' }).first()
  for (const [enlace, titulo] of [
    ['Buscar', 'Buscar vehículo'],
    ['Comparador', 'Comparador'],
    ['Reviews', 'Reviews honestas'],
    ['Actualizados', 'Vehículos actualizados'],
  ]) {
    await nav.getByRole('button', { name: 'Vehículos' }).click()
    await nav.getByRole('menuitem', { name: enlace, exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: titulo })).toBeVisible()
  }
  await page.getByRole('link', { name: 'MiProximoCarro, inicio' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText(/^¿[^?]+\?$/)
})
