#!/usr/bin/env python3
"""
日志管理工具
用于查看、分析和管理API请求日志
"""

import os
import json
import argparse
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Iterator, Optional
import glob

class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
    
    def get_log_files(self) -> List[Path]:
        """获取所有日志文件（仅支持未压缩的.log文件）"""
        if not self.log_dir.exists():
            return []
        
        # 只查找普通的.log文件
        log_files = []
        log_files.extend(self.log_dir.glob("*.log"))
        
        return sorted(log_files)
    
    def _open_log_file(self, file_path: Path):
        """打开日志文件（仅支持普通文本文件）"""
        return open(file_path, 'r', encoding='utf-8')
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """健壮的时间戳解析"""
        # 移除可能的微秒部分
        clean_timestamp = timestamp_str.split('.')[0]
        
        # 尝试多种时间格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%m-%d %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(clean_timestamp, fmt)
            except ValueError:
                continue
                
        return None
    
    def parse_log_line(self, line: str) -> Dict:
        """改进的日志行解析"""
        try:
            # 使用正则表达式更准确地解析日志格式
            # 格式: YYYY-MM-DD HH:mm:ss | LEVEL | location | message
            pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*\|\s*([A-Z]+)\s*\|\s*([^|]+)\s*-\s*(.+)$'
            match = re.match(pattern, line.strip())
            
            if match:
                timestamp, level, location, message = match.groups()
                
                # 尝试解析结构化消息
                if " | " in message:
                    msg_parts = message.split(" | ", 1)
                    event_type = msg_parts[0].strip()
                    
                    if len(msg_parts) > 1:
                        json_part = msg_parts[1].strip()
                        try:
                            json_data = json.loads(json_part)
                            return {
                                "timestamp": timestamp,
                                "level": level.strip(),
                                "location": location.strip(),
                                "event_type": event_type,
                                "data": json_data,
                                "parsed": True
                            }
                        except json.JSONDecodeError:
                            # JSON解析失败，当作普通消息处理
                            pass
                
                return {
                    "timestamp": timestamp,
                    "level": level.strip(),
                    "location": location.strip(),
                    "message": message.strip(),
                    "parsed": True
                }
            
            # 如果正则匹配失败，尝试简单的分割
            parts = line.split(" | ", 3)
            if len(parts) >= 4:
                return {
                    "timestamp": parts[0].strip(),
                    "level": parts[1].strip(),
                    "location": parts[2].strip(),
                    "message": parts[3].strip(),
                    "parsed": True
                }
                
        except Exception as e:
            # 解析失败时记录原始行
            return {
                "raw_line": line.strip(),
                "parse_error": str(e),
                "parsed": False
            }
        
        return {
            "raw_line": line.strip(),
            "parsed": False
        }
    
    def analyze_requests(self, days: int = 1) -> Dict:
        """分析请求统计（优化版本）"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "endpoints": {},
            "error_types": {},
            "auth_failures": 0,
            "client_ips": {}
        }
        
        print(f"📊 开始分析最近 {days} 天的日志...")
        log_files = self.get_log_files()
        
        for i, log_file in enumerate(log_files):
            print(f"处理文件 {i+1}/{len(log_files)}: {log_file.name}")
            self._process_log_file(log_file, cutoff_time, stats)
        
        print("\n✅ 统计分析完成")
        return stats
        
    def _process_log_file(self, log_file: Path, cutoff_time: datetime, stats: Dict):
        """处理单个日志文件的统计"""
        try:
            # 检查文件大小，跳过太大的文件
            file_size = log_file.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB
                print(f"⚠️  跳过大文件: {log_file.name} ({file_size / 1024 / 1024:.1f}MB)", file=sys.stderr)
                return
            
            with self._open_log_file(log_file) as f:
                line_count = 0
                for line in f:
                    line_count += 1
                    if line_count % 10000 == 0:  # 每处理10000行显示进度
                        print(f"处理 {log_file.name}: {line_count} 行", end='\r')
                    
                    parsed = self.parse_log_line(line)
                    
                    if not parsed.get("parsed") or "data" not in parsed:
                        continue
                    
                    data = parsed["data"]
                    event_type = parsed.get("event_type", "")
                    
                    # 检查时间是否在范围内
                    log_time = self._parse_timestamp(parsed["timestamp"])
                    if not log_time or log_time < cutoff_time:
                        continue
                    
                    # 统计逻辑
                    if "REQUEST_END" in event_type:
                        stats["total_requests"] += 1
                        
                        if data.get("success", False):
                            stats["successful_requests"] += 1
                        else:
                            stats["failed_requests"] += 1
                            error = data.get("error", "Unknown")
                            stats["error_types"][error] = stats["error_types"].get(error, 0) + 1
                        
                        # 统计端点
                        endpoint = data.get("endpoint", "unknown")
                        if endpoint not in stats["endpoints"]:
                            stats["endpoints"][endpoint] = {"count": 0, "success": 0, "failed": 0}
                        
                        stats["endpoints"][endpoint]["count"] += 1
                        if data.get("success", False):
                            stats["endpoints"][endpoint]["success"] += 1
                        else:
                            stats["endpoints"][endpoint]["failed"] += 1
                    
                    elif "REQUEST_START" in event_type:
                        client_ip = data.get("client_ip", "unknown")
                        stats["client_ips"][client_ip] = stats["client_ips"].get(client_ip, 0) + 1
                    
                    elif "AUTH_FAILURE" in event_type:
                        stats["auth_failures"] += 1
                
        except Exception as e:
            print(f"读取日志文件失败 {log_file}: {e}", file=sys.stderr)
        
        return stats
    
    def show_recent_errors(self, hours: int = 24, limit: int = 10) -> Iterator[Dict]:
        """显示最近的错误（生成器版本，内存友好）"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        error_count = 0
        
        # 按文件修改时间倒序处理（最新的文件先处理）
        log_files = sorted(self.get_log_files(), 
                          key=lambda x: x.stat().st_mtime, 
                          reverse=True)
        
        for log_file in log_files:
            # 跳过太旧的文件
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_time - timedelta(days=1):
                continue
            
            try:
                with self._open_log_file(log_file) as f:
                    # 读取所有行并倒序处理（最新的行先处理）
                    all_lines = f.readlines()
                    
                    for line in reversed(all_lines):
                        parsed = self.parse_log_line(line)
                        
                        if not parsed.get("parsed"):
                            continue
                        
                        # 检查是否是错误或警告
                        is_error = (parsed.get("level") in ["ERROR", "WARNING"] or 
                                   "ERROR" in parsed.get("event_type", "") or
                                   "AUTH_FAILURE" in parsed.get("event_type", ""))
                        
                        if is_error:
                            log_time = self._parse_timestamp(parsed["timestamp"])
                            if log_time and log_time >= cutoff_time:
                                yield parsed
                                error_count += 1
                                
                                if error_count >= limit:
                                    return
                    
            except Exception as e:
                print(f"读取日志文件失败 {log_file}: {e}", file=sys.stderr)
    
    def cleanup_old_logs(self, days: int = 30):
        """清理旧日志文件"""
        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned_files = []
        
        for log_file in self.get_log_files():
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_time:
                    log_file.unlink()
                    cleaned_files.append(log_file.name)
            except Exception as e:
                print(f"删除日志文件失败 {log_file}: {e}", file=sys.stderr)
        
        return cleaned_files

def main():
    parser = argparse.ArgumentParser(description="API日志管理工具")
    parser.add_argument("--log-dir", default="logs", help="日志目录路径")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 列出日志文件
    list_parser = subparsers.add_parser("list", help="列出所有日志文件")
    
    # 分析请求统计
    stats_parser = subparsers.add_parser("stats", help="分析请求统计")
    stats_parser.add_argument("--days", type=int, default=1, help="分析最近几天的数据")
    
    # 显示最近错误
    errors_parser = subparsers.add_parser("errors", help="显示最近的错误")
    errors_parser.add_argument("--hours", type=int, default=24, help="显示最近几小时的错误")
    errors_parser.add_argument("--limit", type=int, default=10, help="显示错误的最大数量")
    
    # 清理旧日志
    cleanup_parser = subparsers.add_parser("cleanup", help="清理旧日志文件")
    cleanup_parser.add_argument("--days", type=int, default=30, help="清理多少天前的日志")
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer(args.log_dir)
    
    if args.command == "list":
        files = analyzer.get_log_files()
        if files:
            print("📁 日志文件列表:")
            for file in files:
                stat = file.stat()
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime)
                print(f"  {file.name} ({size:,} bytes, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print("📁 未找到日志文件")
    
    elif args.command == "stats":
        stats = analyzer.analyze_requests(args.days)
        
        print(f"📊 最近 {args.days} 天的请求统计:")
        print(f"  总请求数: {stats['total_requests']}")
        print(f"  成功请求: {stats['successful_requests']}")
        print(f"  失败请求: {stats['failed_requests']}")
        print(f"  认证失败: {stats['auth_failures']}")
        
        if stats['endpoints']:
            print(f"\n📍 端点统计:")
            for endpoint, data in sorted(stats['endpoints'].items(), key=lambda x: x[1]['count'], reverse=True):
                print(f"  {endpoint}: {data['count']} 次 (成功: {data['success']}, 失败: {data['failed']})")
        
        if stats['client_ips']:
            print(f"\n🌐 客户端IP统计:")
            for ip, count in sorted(stats['client_ips'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {ip}: {count} 次")
        
        if stats['error_types']:
            print(f"\n❌ 错误类型统计:")
            for error, count in sorted(stats['error_types'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count} 次")
    
    elif args.command == "errors":
        print(f"❌ 查找最近 {args.hours} 小时的错误 (最多 {args.limit} 条)...")
        
        error_found = False
        for error in analyzer.show_recent_errors(args.hours, args.limit):
            if not error_found:
                print(f"\n❌ 最近 {args.hours} 小时的错误:")
                error_found = True
                
            timestamp = error.get("timestamp", "unknown")
            level = error.get("level", "unknown")
            message = error.get("message", "")
            data = error.get("data", {})
            
            print(f"\n⏰ {timestamp} [{level}]")
            if data:
                print(f"  📍 端点: {data.get('endpoint', 'unknown')}")
                print(f"  💬 错误: {data.get('error', data.get('message', 'unknown'))}")
                if 'client_ip' in data:
                    print(f"  🌐 客户端: {data['client_ip']}")
            else:
                print(f"  💬 消息: {message}")
        
        if not error_found:
            print(f"✅ 最近 {args.hours} 小时内没有错误")
    
    elif args.command == "cleanup":
        cleaned = analyzer.cleanup_old_logs(args.days)
        
        if cleaned:
            print(f"🗑️  清理了 {len(cleaned)} 个旧日志文件:")
            for file in cleaned:
                print(f"  - {file}")
        else:
            print(f"✅ 没有需要清理的旧日志文件 (超过 {args.days} 天)")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
