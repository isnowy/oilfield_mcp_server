# MCP 服务器端权限控制实现指南

## 问题说明

当前状态：LibreChat 正确传递了用户信息到 MCP 服务器，但 MCP 服务器没有根据这些信息进行权限控制，导致所有用户都能看到所有数据。

## LibreChat 传递的请求头

```http
X-User-Role: ADMIN 或 USER
X-User-Email: user@example.com
X-User-ID: 697c0cbebb4a93216518c3f9
```

## 需要在 MCP 服务器实现的权限控制

### 方案1：Python FastAPI 实现

```python
from fastapi import FastAPI, Header, HTTPException
from typing import Optional, List, Dict
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟数据库
WELLS_DATABASE = [
    {
        "id": "ZT-102",
        "name": "中塔-102",
        "block": "Block-A",
        "type": "水平井",
        "depth": 4500,
        "team": "Team-701",
        "status": "Active",
        "owner_user_id": "697c0cbebb4a93216518c3f9",  # user1
        "owner_email": "user1@test.com"
    },
    {
        "id": "ZT-105",
        "name": "中塔-105",
        "block": "Block-A",
        "type": "直井",
        "depth": 4200,
        "team": "Team-702",
        "status": "Active",
        "owner_user_id": "697c0cbebb4a93216518c3fd",  # user2
        "owner_email": "user2@test.com"
    },
    {
        "id": "XY-009",
        "name": "新疆-009",
        "block": "Block-B",
        "type": "水平井",
        "depth": 5500,
        "team": "Team-808",
        "status": "Active",
        "owner_user_id": "697c0cbebb4a93216518c3f9",  # user1
        "owner_email": "user1@test.com"
    },
    {
        "id": "ZT-108",
        "name": "中塔-108",
        "block": "Block-A",
        "type": "定向井",
        "depth": 5000,
        "team": "Team-701",
        "status": "Completed",
        "owner_user_id": None,  # 公共数据
        "owner_email": None
    }
]

def filter_wells_by_permission(
    wells: List[Dict],
    user_role: str,
    user_id: str,
    user_email: str
) -> List[Dict]:
    """
    根据用户角色过滤井数据
    
    权限规则：
    - ADMIN: 可以查看所有井
    - USER: 只能查看自己拥有的井 + 公共数据
    """
    if user_role == "ADMIN":
        logger.info(f"ADMIN用户 {user_email} 访问所有数据")
        return wells
    
    elif user_role == "USER":
        # 普通用户只能看到：
        # 1. owner_user_id 是自己的
        # 2. owner_user_id 为 None 的公共数据
        filtered = [
            well for well in wells
            if well.get("owner_user_id") == user_id or well.get("owner_user_id") is None
        ]
        logger.info(f"USER用户 {user_email} 访问 {len(filtered)}/{len(wells)} 条数据")
        return filtered
    
    else:
        # 未知角色，不返回任何数据
        logger.warning(f"未知角色 {user_role}，拒绝访问")
        return []

@app.get("/api/wells")
async def search_wells(
    x_user_role: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
):
    """
    查询井数据 - 带权限控制
    """
    # 记录接收到的请求头
    logger.info("=" * 60)
    logger.info("收到井数据查询请求")
    logger.info(f"  X-User-Role: {x_user_role}")
    logger.info(f"  X-User-Email: {x_user_email}")
    logger.info(f"  X-User-ID: {x_user_id}")
    logger.info("=" * 60)
    
    # 验证必需的请求头
    if not x_user_role or not x_user_id:
        raise HTTPException(
            status_code=401,
            detail="缺少用户认证信息"
        )
    
    # 根据权限过滤数据
    filtered_wells = filter_wells_by_permission(
        WELLS_DATABASE,
        x_user_role,
        x_user_id,
        x_user_email or "unknown"
    )
    
    # 统计并返回
    active_wells = [w for w in filtered_wells if w["status"] == "Active"]
    completed_wells = [w for w in filtered_wells if w["status"] == "Completed"]
    
    return {
        "user_info": {
            "role": x_user_role,
            "email": x_user_email,
            "user_id": x_user_id
        },
        "summary": {
            "total": len(filtered_wells),
            "active": len(active_wells),
            "completed": len(completed_wells)
        },
        "wells": {
            "active": active_wells,
            "completed": completed_wells
        }
    }

@app.get("/api/wells/{well_id}")
async def get_well_detail(
    well_id: str,
    x_user_role: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
):
    """
    获取单个井的详细信息 - 带权限控制
    """
    logger.info(f"查询井详情: {well_id} (用户: {x_user_email}, 角色: {x_user_role})")
    
    if not x_user_role or not x_user_id:
        raise HTTPException(status_code=401, detail="缺少用户认证信息")
    
    # 查找井
    well = next((w for w in WELLS_DATABASE if w["id"] == well_id), None)
    if not well:
        raise HTTPException(status_code=404, detail="井不存在")
    
    # 权限检查
    if x_user_role != "ADMIN":
        # 普通用户只能查看自己的井或公共井
        if well.get("owner_user_id") not in [x_user_id, None]:
            raise HTTPException(
                status_code=403,
                detail="您没有权限访问此井的数据"
            )
    
    return {
        "well": well,
        "access_granted_by": x_user_role
    }

# MCP SSE 端点
@app.get("/sse")
async def mcp_sse_endpoint(
    x_user_role: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
):
    """
    MCP Server-Sent Events 端点
    """
    logger.info("=" * 60)
    logger.info("MCP SSE 连接建立")
    logger.info(f"  用户角色: {x_user_role}")
    logger.info(f"  用户邮箱: {x_user_email}")
    logger.info(f"  用户ID: {x_user_id}")
    logger.info("=" * 60)
    
    # 这里实现你的 MCP 协议逻辑
    # 确保所有数据查询都使用上面的权限过滤函数
    
    return {
        "message": "MCP endpoint",
        "user_role": x_user_role,
        "user_email": x_user_email
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### 方案2：Node.js/Express 实现

```javascript
const express = require('express');
const app = express();

// 模拟数据库
const WELLS_DATABASE = [
  {
    id: "ZT-102",
    name: "中塔-102",
    block: "Block-A",
    type: "水平井",
    depth: 4500,
    team: "Team-701",
    status: "Active",
    ownerUserId: "697c0cbebb4a93216518c3f9",  // user1
    ownerEmail: "user1@test.com"
  },
  {
    id: "ZT-105",
    name: "中塔-105",
    block: "Block-A",
    type: "直井",
    depth: 4200,
    team: "Team-702",
    status: "Active",
    ownerUserId: "697c0cbebb4a93216518c3fd",  // user2
    ownerEmail: "user2@test.com"
  },
  {
    id: "XY-009",
    name: "新疆-009",
    block: "Block-B",
    type: "水平井",
    depth: 5500,
    team: "Team-808",
    status: "Active",
    ownerUserId: "697c0cbebb4a93216518c3f9",  // user1
    ownerEmail: "user1@test.com"
  },
  {
    id: "ZT-108",
    name: "中塔-108",
    block: "Block-A",
    type: "定向井",
    depth: 5000,
    team: "Team-701",
    status: "Completed",
    ownerUserId: null,  // 公共数据
    ownerEmail: null
  }
];

// 权限过滤函数
function filterWellsByPermission(wells, userRole, userId, userEmail) {
  console.log('='.repeat(60));
  console.log(`权限过滤: 角色=${userRole}, 用户=${userEmail}, ID=${userId}`);
  
  if (userRole === 'ADMIN') {
    console.log(`ADMIN用户访问所有 ${wells.length} 条数据`);
    return wells;
  }
  
  if (userRole === 'USER') {
    const filtered = wells.filter(well => 
      well.ownerUserId === userId || well.ownerUserId === null
    );
    console.log(`USER用户访问 ${filtered.length}/${wells.length} 条数据`);
    return filtered;
  }
  
  console.log('未知角色，拒绝访问');
  return [];
}

// 中间件：记录请求头
app.use((req, res, next) => {
  const userRole = req.headers['x-user-role'];
  const userEmail = req.headers['x-user-email'];
  const userId = req.headers['x-user-id'];
  
  console.log('\n' + '='.repeat(60));
  console.log('收到请求:', req.method, req.path);
  console.log('  X-User-Role:', userRole);
  console.log('  X-User-Email:', userEmail);
  console.log('  X-User-ID:', userId);
  console.log('='.repeat(60) + '\n');
  
  next();
});

// API: 查询井列表
app.get('/api/wells', (req, res) => {
  const userRole = req.headers['x-user-role'];
  const userEmail = req.headers['x-user-email'];
  const userId = req.headers['x-user-id'];
  
  if (!userRole || !userId) {
    return res.status(401).json({ error: '缺少用户认证信息' });
  }
  
  // 权限过滤
  const filteredWells = filterWellsByPermission(
    WELLS_DATABASE,
    userRole,
    userId,
    userEmail
  );
  
  // 统计
  const activeWells = filteredWells.filter(w => w.status === 'Active');
  const completedWells = filteredWells.filter(w => w.status === 'Completed');
  
  res.json({
    userInfo: { role: userRole, email: userEmail, userId },
    summary: {
      total: filteredWells.length,
      active: activeWells.length,
      completed: completedWells.length
    },
    wells: {
      active: activeWells,
      completed: completedWells
    }
  });
});

// API: 查询单个井详情
app.get('/api/wells/:wellId', (req, res) => {
  const userRole = req.headers['x-user-role'];
  const userId = req.headers['x-user-id'];
  const { wellId } = req.params;
  
  if (!userRole || !userId) {
    return res.status(401).json({ error: '缺少用户认证信息' });
  }
  
  const well = WELLS_DATABASE.find(w => w.id === wellId);
  if (!well) {
    return res.status(404).json({ error: '井不存在' });
  }
  
  // 权限检查
  if (userRole !== 'ADMIN') {
    if (well.ownerUserId !== userId && well.ownerUserId !== null) {
      return res.status(403).json({ error: '您没有权限访问此井的数据' });
    }
  }
  
  res.json({ well, accessGrantedBy: userRole });
});

// MCP SSE 端点
app.get('/sse', (req, res) => {
  const userRole = req.headers['x-user-role'];
  const userEmail = req.headers['x-user-email'];
  const userId = req.headers['x-user-id'];
  
  console.log('MCP SSE 连接建立');
  console.log(`  用户: ${userEmail} (${userRole})`);
  
  // 这里实现你的 MCP 协议逻辑
  // 确保使用 filterWellsByPermission 进行权限控制
  
  res.json({
    message: 'MCP endpoint',
    userRole,
    userEmail
  });
});

app.listen(8080, () => {
  console.log('MCP服务器运行在 http://localhost:8080');
  console.log('已启用基于角色的权限控制');
});
```

## 权限规则说明

### ADMIN 用户
- ✅ 可以查看所有井的数据
- ✅ 可以访问所有用户创建的数据
- ✅ 无任何限制

### USER 用户
- ✅ 可以查看自己创建的井（`owner_user_id` 匹配）
- ✅ 可以查看公共井（`owner_user_id` 为 null）
- ❌ 不能查看其他用户创建的井

## 测试效果

### Admin 登录后查询
```
请求头:
  X-User-Role: ADMIN
  X-User-Email: admin@test.com
  
返回: 4口井（所有数据）
```

### User1 登录后查询
```
请求头:
  X-User-Role: USER
  X-User-Email: user1@test.com
  X-User-ID: 697c0cbebb4a93216518c3f9
  
返回: 3口井
  - ZT-102 (owner: user1)
  - XY-009 (owner: user1)
  - ZT-108 (公共数据)
```

### User2 登录后查询
```
请求头:
  X-User-Role: USER
  X-User-Email: user2@test.com
  X-User-ID: 697c0cbebb4a93216518c3fd
  
返回: 2口井
  - ZT-105 (owner: user2)
  - ZT-108 (公共数据)
```

## 关键实现点

1. **读取请求头**：从 `X-User-Role`, `X-User-Email`, `X-User-ID` 获取用户信息

2. **权限验证**：检查用户是否有权限访问请求的数据

3. **数据过滤**：根据用户角色和ID过滤返回的数据

4. **日志记录**：记录每次访问，便于审计和调试

5. **错误处理**：
   - 401: 缺少认证信息
   - 403: 无权限访问
   - 404: 资源不存在

## 下一步

1. 在你的 MCP 服务器代码中添加上述权限控制逻辑
2. 重启 MCP 服务器
3. 用不同角色的用户登录 LibreChat 测试
4. 观察服务器日志，确认权限过滤生效

现在 LibreChat 端已经完美配置好了，只需要在 MCP 服务器端实现这些权限控制逻辑即可！
