#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻采集器基类
"""

from typing import List, Dict


class NewsScraper:
    """新闻采集器基类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索新闻，返回标题和URL列表
        
        Args:
            keyword: 搜索关键字
            
        Returns:
            包含 title, url, platform 的字典列表
        """
        raise NotImplementedError
