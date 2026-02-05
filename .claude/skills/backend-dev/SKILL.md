---
name: backend-dev
description: 开发后端backend程序，backend是重要模块。提供后端的重要功能。
---

1. 只允许修改TokenMachine/backend下的代码。对于其他路径没有修改权限，但是有ui和worker只读权限。当需要ui进行修改时，提出需求并写入need.md。
2. 使用机器开发环境，使用8001端口作为自身的开发环境使用端口，默认启动debug模式，防止反复重启接口。
3. 测试文件TokenMachine/backend/tests内，测试要求要严格，不允许降低要求让测试通过导致假阳性通过。保障在与前端联调时，自身接口不出问题。

