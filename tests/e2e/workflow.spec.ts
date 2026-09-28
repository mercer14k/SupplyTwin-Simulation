import {test,expect} from '../../apps/web/node_modules/@playwright/test';
import path from 'node:path';

test('baseline → disruption → evidence → replay → version → import validation',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.getByRole('heading',{name:'See the ripple effect.'})).toBeVisible();
 await page.getByRole('button',{name:'Run comparison',exact:true}).click();
 await expect(page.getByText('Conservation checks passed')).toBeVisible();
 await expect(page.locator('.kpi').first()).toContainText('94.4%');
 await page.screenshot({path:'../../output/playwright/workspace.png',fullPage:true});
 await page.locator('.kpi').first().click();await expect(page.getByRole('dialog')).toContainText('kpi:fill_rate');
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.getByRole('button',{name:'Explain deltas'}).click();await expect(page.getByRole('heading',{name:'Computed explanation'})).toBeVisible();
 await page.getByRole('button',{name:'Replay seed'}).click();await expect(page.getByText('Conservation checks passed')).toBeVisible();
 await page.getByRole('button',{name:'Save version',exact:true}).click();await expect(page.getByRole('status')).toContainText('Saved');
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export scenario JSON'}).click();const download=await downloadPromise;expect(download.suggestedFilename()).toMatch(/\.json$/);
 await page.getByRole('button',{name:'Network & data',exact:true}).click();await page.getByRole('textbox',{name:'Search network'}).fill('Austin');await expect(page.getByRole('cell',{name:'Austin Assembly'})).toBeVisible();await expect(page.getByRole('cell',{name:'Osaka Components'})).toHaveCount(0);
 await page.getByLabel('Import network', {exact:true}).setInputFiles(path.resolve('../../data/sample/invalid-network.json'));
 await expect(page.getByText('nodes.0.capacity')).toBeVisible();await expect(page.getByText('lanes.0.lead_time')).toBeVisible();
 await page.getByRole('button',{name:'Architecture',exact:true}).click();await expect(page.getByRole('heading',{name:'Model boundaries'})).toBeVisible();
 expect(errors).toEqual([]);
});

test('mobile layout remains usable and scenario library opens templates',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.getByRole('button',{name:'Run comparison',exact:true})).toBeEnabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.getByRole('button',{name:'Scenario library',exact:true}).click();await expect(page.getByRole('heading',{name:'Chicago DC outage'})).toBeVisible();
 await page.getByRole('button',{name:'Open scenario'}).first().click();await expect(page.getByRole('heading',{name:'See the ripple effect.'})).toBeVisible();
 await page.screenshot({path:'../../output/playwright/mobile.png',fullPage:true});
});
