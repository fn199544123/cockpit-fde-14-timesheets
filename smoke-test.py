#!/usr/bin/env python3
"""在宿主机执行 python3 smoke-test.py；仅使用临时浏览器上下文和本地回环服务。"""
import json, threading, functools, http.server
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[]
def check(name, condition):
    if not condition: raise AssertionError(name)
    checks.append({'name':name,'status':'passed'})
try:
 with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True)
    page=context.new_page(); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}/index.html')
    check('初始演示数据成本与工时',page.locator('#metric0').inner_text()=='26 h' and page.locator('#metric1').inner_text()=='¥4,640.00')
    page.locator('#newEntry').click();page.locator('#eProject').select_option('P-002');page.locator('#ePerson').select_option('R-002')
    for value in ['-1','25','0']:
        page.locator('#eHours').fill(value);page.locator('button[type=submit]').click()
        check('拒绝非法工时 '+value,'工时必须' in page.locator('#formError').inner_text() and page.locator('#editor').is_visible())
    page.locator('#eHours').fill('17');page.locator('button[type=submit]').click()
    check('拒绝人员单日跨记录累计超过24小时','累计不能超过 24' in page.locator('#formError').inner_text())
    page.locator('#eHours').fill('4');page.locator('button[type=submit]').click()
    check('记工后成本增加600元',page.locator('#metric1').inner_text()=='¥5,240.00')
    check('超预算提示联动',page.locator('#metric3').inner_text()=='1 个' and '超预算 ¥240.00' in page.locator('#table').inner_text())
    page.reload();check('刷新持久化',page.locator('#metric1').inner_text()=='¥5,240.00')
    page.locator('[data-tab=entries]').click();page.locator('[data-edit="E-005"]').click();page.locator('#eHours').fill('2');page.locator('button[type=submit]').click()
    check('修改工时成本与预警回落',page.locator('#metric1').inner_text()=='¥4,940.00' and page.locator('#metric3').inner_text()=='0 个')
    page.locator('[data-tab=people]').click();page.locator('[data-edit="R-002"]').click();page.locator('#eRate').fill('220');page.locator('button[type=submit]').click()
    check('调薪不重算历史成本',page.locator('#metric1').inner_text()=='¥4,940.00')
    page.locator('#add').click();page.locator('#eName').fill('化名丁');page.locator('#eRate').fill('100');page.locator('button[type=submit]').click()
    check('新增人员', '化名丁' in page.locator('#table').inner_text())
    page.locator('[data-tab=projects]').click();page.locator('#add').click();page.locator('#eBudget').fill('100');page.locator('button[type=submit]').click()
    check('新增项目预算','P-004' in page.locator('#table').inner_text())
    page.locator('#newEntry').click();page.locator('#eProject').select_option('P-004');page.locator('#ePerson').select_option('R-004');page.locator('#eHours').fill('2');page.locator('button[type=submit]').click()
    check('新增人员项目可登记并超预算',page.locator('#metric1').inner_text()=='¥5,140.00' and page.locator('#metric3').inner_text()=='1 个')
    page.locator('[data-edit="P-004"]').click();page.locator('#eBudget').fill('300');page.locator('button[type=submit]').click()
    check('修改预算更新预警',page.locator('#metric3').inner_text()=='0 个')
    page.locator('#projectFilter').select_option('P-004');page.locator('#personFilter').select_option('R-004')
    check('项目人员联合筛选',page.locator('#metric0').inner_text()=='2 h' and page.locator('#metric1').inner_text()=='¥200.00')
    page.locator('[data-tab=people]').click();check('人员汇总联动','200' in page.locator('#table').inner_text() and '化名丁' in page.locator('#table').inner_text())
    page.locator('#from').fill('2099-01-01');page.locator('#from').dispatch_event('change');check('日期筛选空状态',page.locator('#metric0').inner_text()=='0 h')
    page.locator('#to').fill('2000-01-01');page.locator('#to').dispatch_event('change');check('日期范围校验',page.locator('#filterError').is_visible())
    page.locator('#clearFilter').click();page.locator('[data-tab=entries]').click();page.locator('#projectFilter').select_option('P-004')
    with page.expect_download() as d: page.locator('#export').click()
    content=Path(d.value.path()).read_text(encoding='utf-8-sig')
    check('CSV导出筛选结果与登记时薪','P-004' in content and 'P-001' not in content and '"100","200"' in content)
    page.once('dialog',lambda d:d.dismiss());page.locator('#reset').click();check('取消重置保留数据', 'P-004' in page.locator('#table').inner_text())
    page.once('dialog',lambda d:d.accept());page.locator('[data-delete="E-006"]').click();check('删除联动',page.locator('#metric0').inner_text()=='0 h')
    page.once('dialog',lambda d:d.accept());page.locator('#reset').click();check('确认重置恢复默认数据',page.locator('#metric1').inner_text()=='¥4,640.00')
    page.locator('#newEntry').click();page.locator('#ePerson').select_option('R-002');page.locator('#eHours').fill('16');page.locator('button[type=submit]').click();check('人员单日累计恰好24小时允许保存',not page.locator('#editor').is_visible())
    page.locator('#newEntry').click();page.locator('#ePerson').select_option('R-002');page.locator('#eHours').fill('0.01');page.locator('button[type=submit]').click();check('跨项目累计超过24小时拒绝','累计不能超过 24' in page.locator('#formError').inner_text());page.locator('#cancel').click()
    page.once('dialog',lambda d:d.accept());page.locator('#reset').click()
    page.locator('#newEntry').click();page.locator('#eProject').select_option('P-002');page.locator('#ePerson').select_option('R-002');page.locator('#eHours').fill('4');page.locator('button[type=submit]').click();page.locator('[data-tab=projects]').click()
    page.screenshot(path=str(ROOT/'evidence-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844});check('手机宽度无页面横向溢出',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    page.locator('#newEntry').click();check('手机可打开工时表单',page.locator('#eHours').is_visible());page.locator('#cancel').click()
    page.screenshot(path=str(ROOT/'evidence-mobile.png'),full_page=True)
    check('localStorage键隔离',page.evaluate("Object.keys(localStorage).every(k=>k.startsWith('development-14-'))"))
    check('浏览器无脚本异常',not errors)
    browser.close()
finally:
 server.shutdown()
 (ROOT/'smoke-test-result.json').write_text(json.dumps({'runner':'宿主机 Python Playwright + Chromium','checks':checks,'passed':len(checks)},ensure_ascii=False,indent=2))
print(json.dumps({'passed':len(checks),'status':'passed'},ensure_ascii=False))
