---
name: gpuagent
description: 开发worker部署的agent程序，worker是一个独立模块。提供在其他节点或本机进行worker安装和配置的功能。
---

worker的定义:一堆gpu的组合，可以是本机的1,2,3卡，可以是远程机器的1,2,3卡，也可以是混合的。一个节点可以包含多个worker，一个worker也可以跨多个节点。一张gpu卡只能属于一个worker。
worker的作用：1.occupy功能，当gpu卡被加入worker时候，占用gpu显存80% 2.exporter功能：worker内所有gpu的metrics接口 3.reciver功能，接受backend下发的大模型启动指令。4.心跳，告诉backend我还活着。
worker的代码结构：TokenMachine/worker/gpu-agent/install.sh（worker注册安装脚本）
1. 只允许修改TokenMachine/worker下的代码。对于backend路径和ui路径没有修改权限，但是有只读权限。当需要后端和ui进行修改时，提出需求并写入need.md。
2. 使用机器开发环境，访问后端和前端默认端口获取数据。
3. 测试文件TokenMachine/worker/tests内，测试要求要严格，不允许降低要求让测试通过导致假阳性通过。保障在与后端前端联调时，gpuagent不出问题。

