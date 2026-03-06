"""
审计日志模块
提供工具调用的审计和追踪功能
"""
import time
import json
import logging
import functools

logger = logging.getLogger(__name__)

class AuditLog:
    """装饰器：用于记录工具调用的输入、输出、耗时和状态"""
    
    @staticmethod
    def trace(tool_name: str):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_ts = time.time()
                trace_id = f"{int(time.time() * 1000)}"[-8:]
                
                try:
                    user_role = kwargs.get('user_role', 'GUEST')
                    logger.info(json.dumps({
                        "event": "TOOL_START",
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "user": user_role,
                        "params": {k: v for k, v in kwargs.items() if k not in ['user_role', 'user_id', 'user_email']}
                    }, ensure_ascii=False))
                    
                    result = func(*args, **kwargs)
                    duration = round((time.time() - start_ts) * 1000, 2)
                    
                    logger.info(json.dumps({
                        "event": "TOOL_SUCCESS",
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "duration_ms": duration,
                        "result_length": len(str(result))
                    }, ensure_ascii=False))
                    
                    return result
                    
                except Exception as e:
                    duration = round((time.time() - start_ts) * 1000, 2)
                    logger.error(json.dumps({
                        "event": "TOOL_ERROR",
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "duration_ms": duration,
                        "error": str(e)
                    }, ensure_ascii=False))
                    
                    return f"⚠️ 系统错误 (TraceID: {trace_id}): {str(e)}"
            
            return wrapper
        return decorator
