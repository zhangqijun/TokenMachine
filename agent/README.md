# TokenMachine GPU Agent

 GPU Worker 管理程序，用于 TokenMachine 平台的 GPU 资源管理。
添加worker默认是单节点的，除非第二次添加（同一个worker token），再去确认和原worker的所有机器的连通状况。 

agent应该为一个系统服务，具备开机自起的能力 
 当第一次添加，先获取所有ip，给server的联通性接口发送所有ip，让server返回所有可以联通的ip。
       若没有，则开启ssh反向代理，创建与server的连接能力。

  需要确保机器的驱动和docker和runtime是否安装
  若没有安装驱动，则提示安装驱动并退出。若安装了驱动，则确认哪些卡是完全没有占用的，当用户选择了哪些卡可以加入worker，则立刻启动占用程序。
  占用完成后，上报server，启动心跳。
  
