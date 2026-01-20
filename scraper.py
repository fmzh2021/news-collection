#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻采集和总结工具
支持头条、Google、Bing 三个平台的新闻搜索
"""

import sys
import json
import re
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin, unquote, parse_qs
import time
from datetime import datetime
from typing import List, Dict, Optional

# 尝试导入Playwright（可选）
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("提示: Playwright未安装，头条动态内容可能无法获取。安装: pip install playwright && playwright install chromium", file=sys.stderr)


class NewsScraper:
    """新闻采集器基类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索新闻，返回标题和URL列表"""
        raise NotImplementedError


class ToutiaoScraper(NewsScraper):
    """头条新闻采集器"""
    
    def search_with_playwright(self, keyword: str) -> List[Dict]:
        """使用Playwright获取动态加载的内容"""
        if not PLAYWRIGHT_AVAILABLE:
            return []
        
        results = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.headers['User-Agent'],
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                
                # 设置额外的HTTP头
                page.set_extra_http_headers({
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Referer': 'https://www.toutiao.com/'
                })
                
                search_url = f"https://so.toutiao.com/search?dvpf=pc&keyword={quote(keyword)}"
                print(f"使用Playwright访问: {search_url}", file=sys.stderr)
                
                # 使用更完善的等待策略，确保页面完全加载
                try:
                    # 第一步：加载页面
                    page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
                    print("DOM内容加载完成", file=sys.stderr)
                    
                    # 第二步：等待网络空闲（但设置较短的超时，避免无限等待）
                    try:
                        page.wait_for_load_state('networkidle', timeout=10000)
                        print("网络请求完成", file=sys.stderr)
                    except PlaywrightTimeoutError:
                        print("网络请求超时，继续处理", file=sys.stderr)
                    
                    # 第三步：等待JavaScript执行完成
                    page.wait_for_timeout(2000)
                    print("等待JavaScript执行...", file=sys.stderr)
                    
                    # 第四步：尝试等待搜索结果出现（多种可能的选择器）
                    selectors_to_wait = [
                        'a[href*="/article/"]',
                        'a[href*="/i"]',
                        '.result-item',
                        '.article-item',
                        '[class*="article"]',
                        '[class*="result"]',
                        'a[href*="toutiao.com"]'
                    ]
                    
                    content_loaded = False
                    for selector in selectors_to_wait:
                        try:
                            page.wait_for_selector(selector, timeout=5000, state='attached')
                            print(f"找到内容元素: {selector}", file=sys.stderr)
                            content_loaded = True
                            break
                        except PlaywrightTimeoutError:
                            continue
                    
                    if not content_loaded:
                        print("未找到预期的内容元素，继续处理", file=sys.stderr)
                    
                    # 第五步：滚动页面触发懒加载
                    print("滚动页面触发懒加载...", file=sys.stderr)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    page.wait_for_timeout(1000)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                    
                    # 第六步：再次等待网络请求
                    try:
                        page.wait_for_load_state('networkidle', timeout=5000)
                        print("懒加载内容加载完成", file=sys.stderr)
                    except PlaywrightTimeoutError:
                        print("懒加载网络请求超时，继续处理", file=sys.stderr)
                    
                    # 第七步：最终等待，确保所有内容渲染完成
                    page.wait_for_timeout(1000)
                    print("页面完全加载完成，开始解析", file=sys.stderr)
                    
                except PlaywrightTimeoutError as e:
                    print(f"页面加载超时: {e}，尝试获取当前内容", file=sys.stderr)
                except Exception as e:
                    print(f"页面加载错误: {e}，继续处理", file=sys.stderr)
                
                # 获取页面HTML
                html_content = page.content()
                print(f"Playwright获取HTML长度: {len(html_content)}", file=sys.stderr)
                
                # 方法0: 解析data-druid-card-data-id中的JSON数据（头条特有格式）
                print("方法0: 解析data-druid-card-data-id中的JSON数据", file=sys.stderr)
                druid_pattern = r'<[^>]+data-druid-card-data-id="([^"]+)"[^>]*>([^<]+)</[^>]+>'
                druid_matches = re.findall(druid_pattern, html_content)
                print(f"找到 {len(druid_matches)} 个druid卡片", file=sys.stderr)
                
                seen = set()
                urls = []
                titles = {}
                
                for data_id, content in druid_matches:
                    if not data_id.startswith('88e2e5f') and len(data_id) < 10:  # 过滤模板代码
                        continue
                    try:
                        data = json.loads(content)
                        if 'data' in data:
                            data_obj = data['data']
                            
                            # 提取标题
                            title = None
                            if 'title' in data_obj:
                                title = data_obj['title']
                            elif 'highlight' in data_obj and isinstance(data_obj['highlight'], dict) and 'title' in data_obj['highlight']:
                                # highlight.title可能是高亮位置数组，需要从原始数据提取
                                title = data_obj.get('title') or ''
                            
                            # 提取URL
                            url = None
                            if 'url' in data_obj:
                                url = data_obj['url']
                            elif 'article_url' in data_obj:
                                url = data_obj['article_url']
                            elif 'share_url' in data_obj:
                                url = data_obj['share_url']
                            elif 'seo_url' in data_obj:
                                url = data_obj['seo_url']
                                if not url.startswith('http'):
                                    url = 'https://toutiao.com' + url
                            elif 'display' in data_obj and isinstance(data_obj['display'], dict) and 'Schema' in data_obj['display']:
                                url = data_obj['display']['Schema']
                            elif 'group_id' in data_obj:
                                url = f"https://toutiao.com/group/{data_obj['group_id']}/"
                            
                            if url and title:
                                # 规范化URL
                                if not url.startswith('http'):
                                    if url.startswith('//'):
                                        url = 'https:' + url
                                    elif url.startswith('/'):
                                        url = 'https://toutiao.com' + url
                                
                                # 验证是有效的新闻URL
                                if ('toutiao.com' in url or 'group' in url) and url not in seen:
                                    seen.add(url)
                                    urls.append(url)
                                    titles[url] = str(title)
                                    
                                    if len(urls) >= 20:
                                        break
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        continue
                
                print(f"从druid卡片提取到 {len(urls)} 个URL", file=sys.stderr)
                
                # 如果druid方法找到结果，直接返回
                if urls:
                    for url in urls[:10]:
                        title = titles.get(url, '')
                        if title and len(title) > 3:
                            results.append({
                                'title': title[:200],
                                'url': url,
                                'platform': 'toutiao'
                            })
                            if len(results) >= 10:
                                break
                    
                    if results:
                        context.close()
                        browser.close()
                        print(f"Playwright从druid卡片获取到 {len(results)} 条结果", file=sys.stderr)
                        return results[:10]
                
                # 方法1: 使用Playwright的API直接查找链接元素
                print("方法1: 使用Playwright API查找链接", file=sys.stderr)
                all_links = page.query_selector_all('a[href]')
                print(f"找到 {len(all_links)} 个链接元素", file=sys.stderr)
                
                # 调试：输出前几个链接的信息
                print("前10个链接详情:", file=sys.stderr)
                for i, link in enumerate(all_links[:10]):
                    try:
                        href = link.get_attribute('href') or ''
                        title_text = link.inner_text() or link.get_attribute('title') or ''
                        print(f"  链接{i+1}: href={href[:80]}, title={title_text[:50]}", file=sys.stderr)
                    except:
                        pass
                
                seen = set()
                urls = []
                titles = {}
                
                for link in all_links[:200]:  # 检查前200个链接
                    try:
                        href = link.get_attribute('href') or ''
                        title_text = link.inner_text() or link.get_attribute('title') or ''
                        title_text = title_text.strip()
                        
                        # 过滤掉无效链接
                        if not href or href.startswith('javascript:') or href.startswith('data:') or href.startswith('#'):
                            continue
                        
                        # 过滤掉图片和其他资源链接
                        if any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.css', '.js']):
                            continue
                        
                        # 更宽松的检查：只要是toutiao.com的链接就考虑
                        is_toutiao_link = (
                            'toutiao.com' in href.lower() or
                            href.startswith('/article/') or
                            (href.startswith('/i') and len(href) > 2) or
                            href.startswith('/a')
                        )
                        
                        if is_toutiao_link:
                            # 规范化URL
                            original_href = href
                            if not href.startswith('http'):
                                if href.startswith('//'):
                                    href = 'https:' + href
                                elif href.startswith('/'):
                                    href = 'https://www.toutiao.com' + href
                            
                            # 排除搜索页面、登录页面等
                            if any(skip in href.lower() for skip in ['/search', '/login', '/register', '/user', '/profile', '/setting']):
                                continue
                            
                            # 更宽松的验证：只要是toutiao.com的链接，且不是搜索页面
                            if 'toutiao.com' in href and '/search' not in href:
                                if href not in seen:
                                    seen.add(href)
                                    urls.append(href)
                                    if title_text and len(title_text) > 3:
                                        titles[href] = title_text
                                    else:
                                        # 如果没有标题，尝试从链接文本获取
                                        link_text = link.inner_text() or ''
                                        if link_text and len(link_text.strip()) > 3:
                                            titles[href] = link_text.strip()
                                    
                                    if len(urls) >= 20:
                                        break
                    except Exception as e:
                        print(f"处理链接时出错: {e}", file=sys.stderr)
                        continue
                
                print(f"从链接元素找到 {len(urls)} 个URL", file=sys.stderr)
                if urls:
                    print(f"找到的URL示例: {urls[0][:100]}", file=sys.stderr)
                
                # 方法2: 如果没找到，使用正则表达式搜索HTML
                if len(urls) == 0:
                    print("方法2: 使用正则表达式搜索HTML", file=sys.stderr)
                    # 头条的URL格式可能是：/article/xxx, /i1234567890, https://www.toutiao.com/article/xxx
                    url_patterns = [
                        r'https?://[^\s"<>]+toutiao\.com[^\s"<>]*(?:/article/|/i\d+|/a\d+)[^\s"<>]*',
                        r'href=["\']([^"\']*(?:/article/|/i\d+|/i/|/a\d+)[^"\']*)["\']',
                        r'["\']([^"\']*(?:/article/|/i\d+|/a\d+)[^"\']*)["\']',
                        r'url["\']?\s*:\s*["\']([^"\']*(?:/article/|/i\d+|/a\d+)[^"\']*)["\']',
                    ]
                    
                    for pattern in url_patterns:
                        matches = re.findall(pattern, html_content, re.IGNORECASE)
                        for match in matches:
                            url = match.strip().strip('"\'')
                            
                            # 过滤掉无效链接
                            if (not url or url.startswith('javascript:') or url.startswith('data:') or 
                                url.startswith('#') or any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.css', '.js'])):
                                continue
                            
                            if not url.startswith('http'):
                                if url.startswith('//'):
                                    url = 'https:' + url
                                elif url.startswith('/'):
                                    url = 'https://www.toutiao.com' + url
                            
                            # 验证是有效的新闻URL
                            is_valid = (
                                url and url not in seen and (
                                    ('toutiao.com' in url and '/article/' in url) or
                                    ('toutiao.com' in url and '/i' in url and '/search' not in url) or
                                    (url.startswith('/article/') or (url.startswith('/i') and len(url) > 2 and url[2:3].isdigit()))
                                )
                            )
                            
                            if is_valid:
                                seen.add(url)
                                urls.append(url)
                                if len(urls) >= 20:
                                    break
                        
                        if len(urls) >= 20:
                            break
                    
                    print(f"正则表达式找到 {len(urls)} 个URL", file=sys.stderr)
                
                # 提取标题和URL，过滤掉无效结果
                for url in urls[:20]:
                    # 再次验证URL有效性
                    if (url.startswith('data:') or url.startswith('javascript:') or 
                        any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico'])):
                        continue
                    
                    # 优先使用已提取的标题
                    title = titles.get(url, '')
                    
                    # 如果没找到标题，尝试从HTML中提取
                    if not title or len(title) < 5:
                        url_escaped = re.escape(url)
                        # 尝试多种模式查找标题
                        title_patterns = [
                            rf'href=["\']{url_escaped}["\'][^>]*>([^<]+)</a>',
                            rf'<a[^>]+href=["\']{url_escaped}["\'][^>]*>([^<]+)</a>',
                            rf'title["\']\s*:\s*["\']([^"\']+)["\'][^>]*{url_escaped}',
                            rf'{url_escaped}[^>]*title=["\']([^"\']+)["\']',
                        ]
                        
                        for pattern in title_patterns:
                            title_match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
                            if title_match:
                                title = title_match.group(1)
                                title = re.sub(r'<[^>]+>', '', title).strip()
                                # 过滤掉base64等无效标题
                                if title and len(title) > 5 and not title.startswith('data:') and 'base64' not in title.lower():
                                    break
                    
                    # 如果还是没找到有效标题，跳过这条记录
                    if not title or len(title) < 5 or title.startswith('data:') or 'base64' in title.lower():
                        print(f"跳过无效URL: {url[:50]}... (标题: {title[:30] if title else 'None'})", file=sys.stderr)
                        continue
                    
                    # 验证标题不是图片数据
                    if len(title) > 100 and title.replace('=', '').replace('/', '').replace('+', '').replace('-', '').isalnum():
                        print(f"跳过疑似base64标题: {url[:50]}...", file=sys.stderr)
                        continue
                    
                    results.append({
                        'title': title[:200],  # 限制标题长度
                        'url': url,
                        'platform': 'toutiao'
                    })
                    
                    if len(results) >= 10:
                        break
                
                context.close()
                browser.close()
                print(f"Playwright获取到 {len(results)} 条结果", file=sys.stderr)
                
        except Exception as e:
            print(f"Playwright错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        
        return results[:10]
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索头条新闻"""
        results = []
        try:
            # 头条搜索URL - 直接使用so.toutiao.com（新搜索域名）
            search_url = f"https://so.toutiao.com/search?dvpf=pc&keyword={quote(keyword)}"
            
            # 添加更多请求头模拟浏览器
            headers = self.headers.copy()
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://www.toutiao.com/'
            })
            
            # 移除Accept-Encoding中的br，因为requests可能不支持brotli
            headers_no_br = headers.copy()
            headers_no_br['Accept-Encoding'] = 'gzip, deflate'
            
            response = requests.get(search_url, headers=headers_no_br, timeout=15, allow_redirects=True)
            
            print(f"头条请求状态码: {response.status_code}", file=sys.stderr)
            print(f"头条响应URL: {response.url}", file=sys.stderr)
            print(f"响应Content-Type: {response.headers.get('Content-Type', 'unknown')}", file=sys.stderr)
            print(f"响应Content-Encoding: {response.headers.get('Content-Encoding', 'none')}", file=sys.stderr)
            
            if response.status_code == 200:
                # 检查响应内容
                content_encoding = response.headers.get('Content-Encoding', '').lower()
                raw_content = response.content
                
                # 如果响应是压缩的但requests没有自动解压
                if content_encoding and 'gzip' in content_encoding:
                    import gzip
                    try:
                        raw_content = gzip.decompress(raw_content)
                        print("手动解压gzip内容", file=sys.stderr)
                    except:
                        pass
                elif content_encoding and 'deflate' in content_encoding:
                    import zlib
                    try:
                        raw_content = zlib.decompress(raw_content)
                        print("手动解压deflate内容", file=sys.stderr)
                    except:
                        pass
                
                # 尝试检测编码
                html_content = None
                import chardet
                detected = chardet.detect(raw_content)
                print(f"检测到的编码: {detected}", file=sys.stderr)
                
                # 尝试多种编码
                encodings_to_try = []
                if detected and detected.get('encoding') and detected.get('confidence', 0) > 0.7:
                    encodings_to_try.append(detected['encoding'])
                
                # 从Content-Type获取编码
                content_type = response.headers.get('Content-Type', '')
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[1].split(';')[0].strip()
                    if charset not in encodings_to_try:
                        encodings_to_try.insert(0, charset)
                
                # 添加常见编码
                encodings_to_try.extend(['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-8-sig'])
                
                for encoding in encodings_to_try:
                    try:
                        html_content = raw_content.decode(encoding)
                        # 验证是否是有效的HTML
                        if '<html' in html_content.lower() or '<body' in html_content.lower() or '<div' in html_content.lower():
                            print(f"成功使用编码: {encoding}", file=sys.stderr)
                            break
                    except (UnicodeDecodeError, LookupError):
                        continue
                
                if not html_content:
                    # 最后尝试，忽略错误
                    html_content = raw_content.decode('utf-8', errors='ignore')
                    print("使用utf-8并忽略错误", file=sys.stderr)
                
                # 首先尝试解析data-druid-card-data-id中的JSON数据（头条特有格式）
                druid_pattern = r'<[^>]+data-druid-card-data-id="([^"]+)"[^>]*>([^<]+)</[^>]+>'
                druid_matches = re.findall(druid_pattern, html_content)
                
                if druid_matches:
                    print(f"找到 {len(druid_matches)} 个druid卡片，尝试解析", file=sys.stderr)
                    seen = set()
                    
                    for data_id, content in druid_matches:
                        if not data_id.startswith('88e2e5f') and len(data_id) < 10:  # 过滤模板代码
                            continue
                        try:
                            data = json.loads(content)
                            if 'data' in data:
                                data_obj = data['data']
                                
                                # 提取标题
                                title = None
                                if 'title' in data_obj:
                                    title = data_obj['title']
                                elif 'highlight' in data_obj and isinstance(data_obj['highlight'], dict):
                                    # 尝试从其他地方获取标题
                                    title = data_obj.get('title') or ''
                                
                                # 提取URL
                                url = None
                                if 'url' in data_obj:
                                    url = data_obj['url']
                                elif 'article_url' in data_obj:
                                    url = data_obj['article_url']
                                elif 'share_url' in data_obj:
                                    url = data_obj['share_url']
                                elif 'seo_url' in data_obj:
                                    url = data_obj['seo_url']
                                    if not url.startswith('http'):
                                        url = 'https://toutiao.com' + url
                                elif 'display' in data_obj and isinstance(data_obj['display'], dict) and 'Schema' in data_obj['display']:
                                    url = data_obj['display']['Schema']
                                elif 'group_id' in data_obj:
                                    url = f"https://toutiao.com/group/{data_obj['group_id']}/"
                                
                                if url and title:
                                    # 规范化URL
                                    if not url.startswith('http'):
                                        if url.startswith('//'):
                                            url = 'https:' + url
                                        elif url.startswith('/'):
                                            url = 'https://toutiao.com' + url
                                    
                                    # 验证是有效的新闻URL
                                    if ('toutiao.com' in url or 'group' in url) and url not in seen:
                                        seen.add(url)
                                        results.append({
                                            'title': str(title)[:200],
                                            'url': url,
                                            'platform': 'toutiao'
                                        })
                                        
                                        if len(results) >= 10:
                                            break
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            continue
                    
                    if results:
                        print(f"从druid卡片提取到 {len(results)} 条结果", file=sys.stderr)
                        return results[:10]
                
                # 尝试多种编码
                encodings_to_try = []
                if detected and detected.get('encoding') and detected.get('confidence', 0) > 0.7:
                    encodings_to_try.append(detected['encoding'])
                
                # 从Content-Type获取编码
                content_type = response.headers.get('Content-Type', '')
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[1].split(';')[0].strip()
                    if charset not in encodings_to_try:
                        encodings_to_try.insert(0, charset)
                
                # 添加常见编码
                encodings_to_try.extend(['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-8-sig'])
                
                for encoding in encodings_to_try:
                    try:
                        html_content = raw_content.decode(encoding)
                        # 验证是否是有效的HTML
                        if '<html' in html_content.lower() or '<body' in html_content.lower() or '<div' in html_content.lower():
                            print(f"成功使用编码: {encoding}", file=sys.stderr)
                            break
                    except (UnicodeDecodeError, LookupError):
                        continue
                
                if not html_content:
                    # 最后尝试，忽略错误
                    html_content = raw_content.decode('utf-8', errors='ignore')
                    print("使用utf-8并忽略错误", file=sys.stderr)
                
                # 调试：保存HTML内容用于分析
                debug_file = os.environ.get('TOUTIAO_DEBUG', '')
                if debug_file:
                    try:
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        print(f"HTML内容已保存到: {debug_file}", file=sys.stderr)
                    except Exception as e:
                        print(f"保存调试文件失败: {e}", file=sys.stderr)
                
                print(f"HTML内容长度: {len(html_content)}", file=sys.stderr)
                # 只打印可打印字符
                printable_content = ''.join(c if c.isprintable() or c in '\n\r\t' else '.' for c in html_content[:500])
                print(f"HTML前500字符(可打印): {printable_content}", file=sys.stderr)
                
                # 检查是否是有效的HTML
                if not ('<' in html_content and '>' in html_content):
                    print("警告: HTML内容可能无效，尝试解压", file=sys.stderr)
                    import gzip
                    try:
                        html_content = gzip.decompress(response.content).decode('utf-8')
                        print("成功解压gzip内容", file=sys.stderr)
                    except:
                        pass
                
                # 尝试不同的解析器
                soup = None
                for parser in ['html.parser', 'lxml', 'html5lib']:
                    try:
                        soup = BeautifulSoup(html_content, parser)
                        print(f"使用解析器: {parser}", file=sys.stderr)
                        break
                    except Exception as e:
                        print(f"解析器 {parser} 失败: {e}", file=sys.stderr)
                        continue
                
                if not soup:
                    print("所有解析器都失败，尝试直接文本搜索", file=sys.stderr)
                    # 直接搜索文本中的链接
                    url_pattern = r'https?://[^\s"<>]+(?:/article/|/i\d+|/a\d+)[^\s"<>]*'
                    urls = re.findall(url_pattern, html_content)
                    title_pattern = r'["\']title["\']\s*:\s*["\']([^"\']+)["\']'
                    titles = re.findall(title_pattern, html_content)
                    
                    print(f"直接搜索找到 {len(urls)} 个URL和 {len(titles)} 个标题", file=sys.stderr)
                    
                    for i, url in enumerate(urls[:10]):
                        title = titles[i] if i < len(titles) else f"新闻 {i+1}"
                        results.append({
                            'title': title,
                            'url': url,
                            'platform': 'toutiao'
                        })
                    
                    if results:
                        return results[:10]
                    else:
                        return []
                
                # 如果soup创建成功，继续使用soup解析
                if soup is None:
                    soup = BeautifulSoup(html_content, 'html.parser')
                
                # 方法1: 尝试查找script标签中的JSON数据
                scripts = soup.find_all('script')
                print(f"找到 {len(scripts)} 个script标签", file=sys.stderr)
                
                # 如果没找到script标签，可能是解析问题，尝试直接搜索HTML文本
                if len(scripts) == 0:
                    print("未找到script标签，尝试在原始HTML中搜索", file=sys.stderr)
                    # 在原始HTML中搜索JSON数据
                    json_patterns = [
                        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
                        r'window\._SSR_HYDRATED_DATA\s*=\s*(\{.*?\});',
                        r'"data"\s*:\s*(\[.*?\]),',
                        r'"list"\s*:\s*(\[.*?\]),',
                    ]
                    
                    for pattern in json_patterns:
                        matches = re.finditer(pattern, html_content, re.DOTALL)
                        for match in matches:
                            try:
                                json_str = match.group(1)
                                data = json.loads(json_str)
                                # 使用之前的extract_items函数
                                def extract_items(obj, depth=0):
                                    if depth > 8:
                                        return []
                                    items = []
                                    if isinstance(obj, dict):
                                        title = (obj.get('title') or obj.get('Title') or obj.get('article_title') or 
                                                obj.get('name') or obj.get('headline'))
                                        url = (obj.get('url') or obj.get('Url') or obj.get('article_url') or 
                                              obj.get('link') or obj.get('source_url') or obj.get('share_url') or
                                              obj.get('article_url') or obj.get('web_url'))
                                        
                                        if title and url:
                                            items.append({'title': str(title), 'url': str(url)})
                                        
                                        for value in obj.values():
                                            items.extend(extract_items(value, depth + 1))
                                    elif isinstance(obj, list):
                                        for item in obj:
                                            items.extend(extract_items(item, depth + 1))
                                    return items
                                
                                items = extract_items(data)
                                for item in items[:10]:
                                    if item.get('title') and item.get('url'):
                                        url = item['url']
                                        if not url.startswith('http'):
                                            url = urljoin('https://www.toutiao.com', url)
                                        results.append({
                                            'title': item['title'],
                                            'url': url,
                                            'platform': 'toutiao'
                                        })
                                if results:
                                    print(f"从原始HTML JSON提取到 {len(results)} 条结果", file=sys.stderr)
                                    break
                            except (json.JSONDecodeError, ValueError) as e:
                                continue
                    
                    if results:
                        return results[:10]
                
                for script in scripts:
                    if script.string:
                        script_text = script.string
                        # 查找包含新闻数据的script标签 - 更广泛的匹配
                        if any(kw in script_text.lower() for kw in ['article', 'news', 'feed', 'list', 'data', 'result', 'item', 'title']):
                            try:
                                # 尝试提取JSON数据 - 使用更宽松的正则
                                json_patterns = [
                                    r'window\._SSR_HYDRATED_DATA\s*=\s*(\{.*?\});',
                                    r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
                                    r'window\.__INITIAL_DATA__\s*=\s*(\{.*?\});',
                                    r'"data"\s*:\s*(\[.*?\])',
                                    r'"list"\s*:\s*(\[.*?\])',
                                    r'"result"\s*:\s*(\[.*?\])',
                                    r'"items"\s*:\s*(\[.*?\])',
                                    # 尝试匹配整个JSON对象
                                    r'(\{[^{}]*"title"[^{}]*"url"[^{}]*\})',
                                    r'(\[[^\[\]]*\{[^}]*"title"[^}]*"url"[^}]*\}[^\[\]]*\])',
                                ]
                                
                                for pattern in json_patterns:
                                    matches = re.finditer(pattern, script_text, re.DOTALL)
                                    for match in matches:
                                        try:
                                            json_str = match.group(1)
                                            # 尝试修复不完整的JSON
                                            if not json_str.strip().startswith('{') and not json_str.strip().startswith('['):
                                                continue
                                            
                                            data = json.loads(json_str)
                                            # 递归查找包含title和url的数据
                                            def extract_items(obj, depth=0):
                                                if depth > 8:  # 增加递归深度
                                                    return []
                                                items = []
                                                if isinstance(obj, dict):
                                                    # 检查是否包含新闻数据
                                                    title = (obj.get('title') or obj.get('Title') or obj.get('article_title') or 
                                                            obj.get('name') or obj.get('headline'))
                                                    url = (obj.get('url') or obj.get('Url') or obj.get('article_url') or 
                                                          obj.get('link') or obj.get('source_url') or obj.get('share_url') or
                                                          obj.get('article_url') or obj.get('web_url'))
                                                    
                                                    if title and url:
                                                        items.append({'title': str(title), 'url': str(url)})
                                                    
                                                    # 递归搜索
                                                    for value in obj.values():
                                                        items.extend(extract_items(value, depth + 1))
                                                elif isinstance(obj, list):
                                                    for item in obj:
                                                        items.extend(extract_items(item, depth + 1))
                                                return items
                                            
                                            items = extract_items(data)
                                            for item in items[:10]:
                                                if item.get('title') and item.get('url'):
                                                    url = item['url']
                                                    if not url.startswith('http'):
                                                        url = urljoin('https://www.toutiao.com', url)
                                                    results.append({
                                                        'title': item['title'],
                                                        'url': url,
                                                        'platform': 'toutiao'
                                                    })
                                            if results:
                                                print(f"从JSON提取到 {len(results)} 条结果", file=sys.stderr)
                                                break
                                        except (json.JSONDecodeError, ValueError) as e:
                                            continue
                                
                                if results:
                                    break
                            except Exception as e:
                                print(f"JSON解析错误: {e}", file=sys.stderr)
                                continue
                
                # 方法2: HTML解析 - 针对so.toutiao.com的改进选择器
                if not results:
                    seen_urls = set()
                    
                    # 策略1: 查找所有包含标题和链接的元素
                    # so.toutiao.com可能使用的类名
                    possible_classes = [
                        'result-item', 'search-result', 'article-item', 'news-item',
                        'feed-item', 'item', 'card', 'result', 'article'
                    ]
                    
                    for class_name in possible_classes:
                        elements = soup.find_all(['div', 'article', 'li'], class_=re.compile(class_name, re.I))
                        print(f"尝试类名 '{class_name}': 找到 {len(elements)} 个元素", file=sys.stderr)
                        
                        for elem in elements:
                            # 查找标题
                            title_elem = (elem.find(['h1', 'h2', 'h3', 'h4', 'h5'], class_=re.compile('title|head', re.I)) or
                                         elem.find('a', class_=re.compile('title|link', re.I)) or
                                         elem.find(['h1', 'h2', 'h3', 'h4', 'h5']) or
                                         elem.find('a'))
                            
                            # 查找链接
                            link_elem = elem.find('a', href=True)
                            
                            if title_elem and link_elem:
                                title = title_elem.get_text(strip=True)
                                href = link_elem.get('href', '')
                                
                                if title and href and len(title) > 5:
                                    if not href.startswith('http'):
                                        href = urljoin('https://www.toutiao.com', href)
                                    
                                    if href not in seen_urls and ('toutiao.com' in href or '/article/' in href or '/i' in href or '/a' in href):
                                        results.append({
                                            'title': title,
                                            'url': href,
                                            'platform': 'toutiao'
                                        })
                                        seen_urls.add(href)
                                        
                                        if len(results) >= 10:
                                            break
                        
                        if results:
                            break
                    
                    # 策略2: 如果还没找到，尝试查找所有链接
                    if not results:
                        print("尝试策略2: 查找所有链接", file=sys.stderr)
                        all_links = soup.find_all('a', href=True)
                        print(f"找到 {len(all_links)} 个链接", file=sys.stderr)
                        
                        # 如果soup没找到链接，尝试在原始HTML中搜索
                        if len(all_links) == 0:
                            print("BeautifulSoup未找到链接，尝试正则表达式搜索", file=sys.stderr)
                            # 使用正则表达式直接搜索HTML中的链接
                            link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
                            link_matches = re.findall(link_pattern, html_content, re.IGNORECASE)
                            print(f"正则表达式找到 {len(link_matches)} 个链接", file=sys.stderr)
                            
                            for href, title_text in link_matches[:20]:
                                title = re.sub(r'<[^>]+>', '', title_text).strip()
                                if title and href and len(title) > 5:
                                    if not href.startswith('http'):
                                        href = urljoin('https://www.toutiao.com', href)
                                    
                                    if href not in seen_urls and ('toutiao.com' in href or '/article/' in href or '/i' in href or '/a' in href):
                                        results.append({
                                            'title': title,
                                            'url': href,
                                            'platform': 'toutiao'
                                        })
                                        seen_urls.add(href)
                                        
                                        if len(results) >= 10:
                                            break
                            
                            if results:
                                print(f"从正则表达式提取到 {len(results)} 条结果", file=sys.stderr)
                                return results[:10]
                        
                        for link in all_links:
                            href = link.get('href', '')
                            title = link.get_text(strip=True)
                            
                            # 过滤有效的新闻链接
                            if (title and len(title) > 10 and href and
                                ('toutiao.com' in href or '/article/' in href or '/i' in href or '/a' in href) and
                                href not in seen_urls and
                                not any(skip in href.lower() for skip in ['javascript:', 'void', '#', 'login', 'register'])):
                                
                                if not href.startswith('http'):
                                    href = urljoin('https://www.toutiao.com', href)
                                
                                results.append({
                                    'title': title,
                                    'url': href,
                                    'platform': 'toutiao'
                                })
                                seen_urls.add(href)
                                
                                if len(results) >= 10:
                                    break
                    
                    if results:
                        print(f"从HTML提取到 {len(results)} 条结果", file=sys.stderr)
                
                # 方法3: 尝试使用so.toutiao.com的API接口
                if not results:
                    # so.toutiao.com可能使用的API端点
                    api_urls = [
                        f"https://so.toutiao.com/api/search/content/?keyword={quote(keyword)}&autoload=true&count=10",
                        f"https://so.toutiao.com/search/api/content/?keyword={quote(keyword)}&count=10",
                    ]
                    
                    for api_url in api_urls:
                        try:
                            api_headers = headers.copy()
                            api_headers['Accept'] = 'application/json, text/plain, */*'
                            api_headers['X-Requested-With'] = 'XMLHttpRequest'
                            
                            api_response = requests.get(api_url, headers=api_headers, timeout=10)
                            print(f"API请求 {api_url}: 状态码 {api_response.status_code}", file=sys.stderr)
                            print(f"API响应Content-Type: {api_response.headers.get('Content-Type', 'unknown')}", file=sys.stderr)
                            print(f"API响应Content-Encoding: {api_response.headers.get('Content-Encoding', 'none')}", file=sys.stderr)
                            
                            if api_response.status_code == 200:
                                try:
                                    # 处理编码
                                    if api_response.encoding is None or api_response.encoding == 'ISO-8859-1':
                                        api_response.encoding = 'utf-8'
                                    
                                    # 检查Content-Type
                                    content_type = api_response.headers.get('Content-Type', '')
                                    
                                    # 尝试解析JSON
                                    api_text = api_response.text
                                    printable_text = ''.join(c if c.isprintable() or c in '\n\r\t' else '.' for c in api_text[:200])
                                    print(f"API响应前200字符(可打印): {printable_text}", file=sys.stderr)
                                    
                                    # 如果看起来像压缩数据，尝试解压
                                    if len(api_text.encode('utf-8', errors='ignore')) < len(api_response.content) * 0.5:
                                        print("检测到可能的压缩数据，尝试解压", file=sys.stderr)
                                        import gzip
                                        try:
                                            api_text = gzip.decompress(api_response.content).decode('utf-8')
                                            print("成功解压API响应", file=sys.stderr)
                                        except:
                                            pass
                                    
                                    if 'json' in content_type.lower():
                                        try:
                                            api_data = json.loads(api_text)
                                        except json.JSONDecodeError:
                                            # 尝试从文本中提取JSON
                                            json_match = re.search(r'\{.*\}', api_text, re.DOTALL)
                                            if json_match:
                                                api_data = json.loads(json_match.group())
                                            else:
                                                print("API返回不是有效的JSON格式，跳过", file=sys.stderr)
                                                continue
                                    else:
                                        # 尝试从HTML中提取JSON
                                        json_match = re.search(r'\{.*\}', api_text, re.DOTALL)
                                        if json_match:
                                            api_data = json.loads(json_match.group())
                                        else:
                                            print("API返回不是JSON格式，跳过", file=sys.stderr)
                                            continue
                                    
                                    print(f"API返回数据类型: {type(api_data)}", file=sys.stderr)
                                    
                                    # 尝试多种数据结构
                                    data_list = []
                                    if isinstance(api_data, dict):
                                        data_list = (api_data.get('data') or api_data.get('result') or 
                                                    api_data.get('list') or api_data.get('items') or [])
                                    elif isinstance(api_data, list):
                                        data_list = api_data
                                    
                                    for item in data_list[:10]:
                                        if isinstance(item, dict):
                                            title = (item.get('title') or item.get('article_title') or 
                                                   item.get('name') or item.get('headline'))
                                            url = (item.get('url') or item.get('article_url') or 
                                                 item.get('share_url') or item.get('link') or item.get('web_url'))
                                            if title and url:
                                                if not url.startswith('http'):
                                                    url = urljoin('https://www.toutiao.com', url)
                                                results.append({
                                                    'title': title,
                                                    'url': url,
                                                    'platform': 'toutiao'
                                                })
                                    
                                    if results:
                                        print(f"从API提取到 {len(results)} 条结果", file=sys.stderr)
                                        break
                                except json.JSONDecodeError:
                                    print(f"API返回不是JSON格式", file=sys.stderr)
                                    continue
                        except Exception as e:
                            print(f"API请求失败 {api_url}: {e}", file=sys.stderr)
                            continue
                            
        except Exception as e:
            print(f"头条搜索错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        
        # 如果所有方法都失败，尝试使用Playwright（如果可用）
        if not results and PLAYWRIGHT_AVAILABLE:
            print("尝试使用Playwright获取动态内容...", file=sys.stderr)
            playwright_results = self.search_with_playwright(keyword)
            if playwright_results:
                results = playwright_results
        
        print(f"头条找到 {len(results)} 条结果", file=sys.stderr)
        return results[:10]  # 确保最多返回10条


class GoogleScraper(NewsScraper):
    """Google新闻采集器"""
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索Google新闻"""
        results = []
        try:
            # Google新闻搜索URL
            search_url = f"https://www.google.com/search?q={quote(keyword)}&tbm=nws"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Google新闻结果通常在div.g中
                articles = soup.find_all('div', class_='g')
                
                for article in articles[:10]:  # 限制前10条
                    title_elem = article.find('h3')
                    link_elem = article.find('a', href=True)
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        link = link_elem.get('href', '')
                        
                        # Google的链接可能是重定向URL，需要提取真实URL
                        if link.startswith('/url?q='):
                            link = unquote(link.split('/url?q=')[1].split('&')[0])
                        elif link.startswith('/url?'):
                            params = parse_qs(link.split('?')[1])
                            if 'q' in params:
                                link = unquote(params['q'][0])
                        
                        # 过滤无效链接
                        if title and link and link.startswith('http'):
                            results.append({
                                'title': title,
                                'url': link,
                                'platform': 'google'
                            })
                
                # 如果div.g没找到，尝试其他选择器
                if not results:
                    # 尝试查找所有包含新闻的链接
                    news_links = soup.find_all('a', href=lambda x: x and ('/url' in x or x.startswith('http')))
                    seen_urls = set()
                    
                    for link_elem in news_links:
                        title = link_elem.get_text(strip=True)
                        href = link_elem.get('href', '')
                        
                        if href.startswith('/url?q='):
                            href = unquote(href.split('/url?q=')[1].split('&')[0])
                        
                        if title and href and href.startswith('http') and href not in seen_urls:
                            results.append({
                                'title': title,
                                'url': href,
                                'platform': 'google'
                            })
                            seen_urls.add(href)
                            
                            if len(results) >= 10:
                                break
                            
        except Exception as e:
            print(f"Google搜索错误: {e}", file=sys.stderr)
        
        return results[:10]  # 确保最多返回10条


class BingScraper(NewsScraper):
    """Bing新闻采集器"""
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索Bing新闻"""
        results = []
        try:
            # Bing新闻搜索URL
            search_url = f"https://www.bing.com/news/search?q={quote(keyword)}"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 方法1: 查找新闻卡片
                articles = soup.find_all(['div', 'article'], class_=lambda x: x and ('news' in x.lower() or 'card' in x.lower() or 'item' in x.lower()))
                
                seen_urls = set()
                
                for article in articles[:15]:  # 多取一些以防过滤后不够
                    # 尝试多种方式查找标题和链接
                    title_elem = None
                    link_elem = None
                    
                    # 查找标题
                    for tag in ['h2', 'h3', 'h4', 'a']:
                        title_elem = article.find(tag, class_=lambda x: x and ('title' in x.lower() if x else False))
                        if title_elem:
                            break
                    if not title_elem:
                        title_elem = article.find(['h2', 'h3', 'h4'])
                    
                    # 查找链接
                    link_elem = article.find('a', href=True)
                    if not link_elem and title_elem and title_elem.name == 'a':
                        link_elem = title_elem
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        link = link_elem.get('href', '')
                        
                        if link and not link.startswith('http'):
                            link = urljoin('https://www.bing.com', link)
                        
                        # 过滤无效结果
                        if (title and len(title) > 5 and link and 
                            link.startswith('http') and link not in seen_urls):
                            results.append({
                                'title': title,
                                'url': link,
                                'platform': 'bing'
                            })
                            seen_urls.add(link)
                            
                            if len(results) >= 10:
                                break
                
                # 方法2: 如果上面没找到，尝试直接查找所有新闻链接
                if not results:
                    all_links = soup.find_all('a', href=True)
                    for link_elem in all_links:
                        href = link_elem.get('href', '')
                        title = link_elem.get_text(strip=True)
                        
                        # 过滤新闻链接
                        if (title and len(title) > 10 and 
                            ('news' in href.lower() or href.startswith('http')) and
                            href not in seen_urls):
                            
                            if not href.startswith('http'):
                                href = urljoin('https://www.bing.com', href)
                            
                            results.append({
                                'title': title,
                                'url': href,
                                'platform': 'bing'
                            })
                            seen_urls.add(href)
                            
                            if len(results) >= 10:
                                break
                            
        except Exception as e:
            print(f"Bing搜索错误: {e}", file=sys.stderr)
        
        return results[:10]  # 确保最多返回10条


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python scraper.py <关键字> [平台列表]")
        print("平台列表: toutiao,google,bing (用逗号分隔)")
        sys.exit(1)
    
    keyword = sys.argv[1]
    platforms_str = sys.argv[2] if len(sys.argv) > 2 else 'toutiao,google,bing'
    platforms = [p.strip().lower() for p in platforms_str.split(',')]
    
    # 创建采集器实例
    scrapers = {
        'toutiao': ToutiaoScraper(),
        'google': GoogleScraper(),
        'bing': BingScraper()
    }
    
    all_results = []
    
    # 遍历每个平台进行搜索
    for platform in platforms:
        if platform not in scrapers:
            print(f"警告: 不支持的平台 '{platform}'，跳过", file=sys.stderr)
            continue
        
        print(f"正在搜索 {platform}...", file=sys.stderr)
        results = scrapers[platform].search(keyword)
        all_results.extend(results)
        
        # 添加延迟避免请求过快
        time.sleep(1)
    
    # 构建输出JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_id = os.environ.get('GITHUB_RUN_ID', 'local')
    run_number = os.environ.get('GITHUB_RUN_NUMBER', '0')
    
    # 生成唯一文件名，避免并发覆盖
    filename = f'results_{run_id}_{run_number}_{timestamp}.json'
    
    output = {
        'keyword': keyword,
        'total': len(all_results),
        'results': all_results,
        'platforms': platforms,
        'timestamp': datetime.now().isoformat(),
        'run_id': run_id,
        'run_number': run_number,
        'filename': filename
    }
    
    # 输出JSON结果
    json_output = json.dumps(output, ensure_ascii=False, indent=2)
    print(json_output)
    
    # 保存到唯一文件名
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    # 同时保存一个latest.json用于快速访问（可选）
    with open('results_latest.json', 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    print(f"\n结果已保存到 {filename} 和 results_latest.json，共找到 {len(all_results)} 条新闻", file=sys.stderr)
    
    # 输出文件名供GitHub Actions使用
    print(f"::set-output name=result_file::{filename}", file=sys.stderr)


if __name__ == '__main__':
    main()
