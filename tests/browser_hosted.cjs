// Explicit, billable Bedrock integration check; not part of the offline test suite.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {execFileSync} = require('node:child_process');
(async () => {
  let input=''; for await(const chunk of process.stdin) input+=chunk;
  const credentials=JSON.parse(input);
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  fs.mkdirSync('artifacts',{recursive:true});
  async function state(){return page.evaluate(()=>JSON.parse(JSON.stringify({run:state.run,workspace:state.workspace,error:state.error})));}
  async function waitStatus(status){
    for(let i=0;i<120;i++){
      const s=await state();
      if(s.run?.status==='FAILED')throw new Error('Workflow failed: '+s.run.error);
      if(s.run?.status===status)return s.run;
      if(i%10===0)console.log('Waiting:',s.run?.status,s.run?.current_node,s.run?.events?.length);
      await page.waitForTimeout(2000);
    }
    throw new Error('Timed out waiting for '+status);
  }
  try {
    await page.goto('https://d2b62i37fl26ui.cloudfront.net/?qa=live1');
    await page.locator('#authUsername').fill(credentials.username);
    await page.locator('#authPassword').fill(credentials.password);
    await page.locator('.auth-submit').click();
    await page.locator('#briefForm').waitFor();
    const inputs={startup_name:'ClearBooks QA',target_acv:'1200.75',sales_cycle_days:'21',total_budget:'1200.25',metric_name:'Qualified bookkeeping demo requests',target_cac:'120.50',minimum_acceptable_volume:'5',one_line_pitch:'Bookkeeping automation for small Singapore consulting businesses. Connect bank statements and reconcile invoices in one place.'};
    for(const [name,value] of Object.entries(inputs))await page.locator(`[name="${name}"]`).fill(value);
    await page.locator('[name="exclude_META"]').check();
    await page.locator('[name="reason_META"]').fill('Focus on B2B buyers with explicit business intent.');
    await page.locator('#briefForm button[type="submit"]').click();
    await page.getByText('Saved to your workspace at',{exact:false}).waitFor();
    await page.reload(); await page.locator('#briefForm').waitFor();
    assert.equal(await page.locator('[name="total_budget"]').inputValue(),'1200.25');
    assert.equal(await page.locator('[name="startup_name"]').inputValue(),'ClearBooks QA');
    console.log('PASS saved brief survives refresh with decimal precision');
    await page.locator('[data-action="start"]').click();
    await page.waitForFunction(()=>state.run?.run_id);
    await page.reload();
    let planned=await waitStatus('WAITING_APPROVAL');
    assert.equal(planned.model_mode,'bedrock');assert.equal(planned.cycle_id,1);
    assert(planned.result.content_package.items.length>0);
    const originalPlan=planned.result.plan;
    await page.locator('a[data-view="approval"]').click();
    await page.getByRole('heading',{name:'Cycle 1 plan',exact:true}).waitFor();
    await page.locator('.content-draft summary').first().click();
    await page.waitForTimeout(4500);
    assert.equal(await page.locator('.content-draft').first().getAttribute('open'),'','Unchanged polls must preserve expanded content');
    await page.screenshot({path:'artifacts/approval-bedrock.png',fullPage:true});
    await page.locator('[name="feedback"]').fill('Keep the total budget unchanged. Use Google Search and Founder Content only; allocate no money to other channels.');
    await page.locator('#revisionForm button').click();
    await page.waitForFunction(()=>state.run?.phase?.startsWith('revise_'));
    planned=await waitStatus('WAITING_APPROVAL');
    assert.notDeepEqual(planned.result.plan,originalPlan);
    console.log('PASS Bedrock strategy, content and revision; approval recovered after refresh');
    await page.locator('a[data-view="approval"]').click();
    await page.locator('[data-action="approve"]').click();
    const complete=await waitStatus('COMPLETE');
    assert.deepEqual(complete.result.plan,planned.result.plan);
    assert(complete.result.analysis_report.verdicts.length>0);
    assert(complete.result.digest_markdown);
    assert(complete.result.results.length>0);
    const strategistCount=complete.events.filter(e=>e.node==='strategist'&&e.status==='started').length;
    assert.equal(strategistCount,2);
    await page.reload(); await page.waitForFunction(()=>state.run?.status==='COMPLETE');
    assert.equal((await state()).run.events.length,complete.events.length);
    await page.evaluate(()=>localStorage.setItem('augury.idToken','expired-test-token'));
    await page.reload(); await page.waitForFunction(()=>state.run?.status==='COMPLETE');
    assert.equal((await state()).run.run_id,complete.run_id,'Refresh-token recovery preserves the workspace');
    await page.screenshot({path:'artifacts/activity-bedrock.png',fullPage:true});
    for(const view of ['dashboard','analytics']){
      await page.locator(`a[data-view="${view}"]`).click();
      await page.screenshot({path:`artifacts/${view}-bedrock.png`,fullPage:true});
    }
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'artifacts/mobile-bedrock.png',fullPage:true});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
    assert.equal(overflow,false,'Mobile page should not overflow horizontally');
    await page.setViewportSize({width:1440,height:1050});
    await page.locator('a[data-view="brief"]').click();
    await page.locator('[data-action="start"]').click();
    await page.waitForFunction(()=>state.run?.cycle_id===2);
    const secondPlan=await waitStatus('WAITING_APPROVAL');
    const previousBudgets=new Map(complete.result.plan.allocations.map(a=>[a.channel,a.proposed_budget]));
    for(const a of secondPlan.result.plan.allocations)assert.equal(a.current_budget,previousBudgets.get(a.channel)||0);
    assert(secondPlan.result.learnings.length>0,'Cycle 2 must load prior learning');
    await page.locator('a[data-view="approval"]').click();
    await page.getByRole('heading',{name:'Cycle 2 plan',exact:true}).waitFor();
    await page.locator('[data-action="approve"]').click();
    await waitStatus('COMPLETE');
    assert.equal((await state()).workspace.runs.length,2);
    assert.deepEqual(errors,[]);
    console.log('PASS execution, analysis, digest, refresh, second cycle, mobile layout; zero browser errors');
    fs.writeFileSync('artifacts/hosted-test-report.json',JSON.stringify({checkedAt:new Date().toISOString(),cycles:2,model:'amazon.nova-lite-v1:0',browserErrors:errors,passed:true},null,2));
  } catch(err) {
    await page.screenshot({path:'artifacts/failure.png',fullPage:true});
    console.error(err.message);
    process.exitCode=1;
  } finally {
    await browser.close();
    execFileSync('python',['scripts/qa_account.py','delete',credentials.username],{stdio:['ignore','ignore','inherit']});
  }
})();
