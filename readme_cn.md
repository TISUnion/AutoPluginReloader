[English](readme.md) | **中文**

Auto Plugin Reloader
-----

一个 [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) (>=2.x) 插件

在 MCDR 插件文件夹中任何插件文件变更时（后缀为 `.py` 或 `.mcdr` 的文件），触发一次插件重载

## 配置

配置文件：`config/auto_plugin_reloader/config.json`

`enabled`：自动重载器开关，默认值：`true`

`permission`：执行指令所需要的最小权限等级，默认值：`4`

`detection_interval_sec`：文件变化检测间的时间间隔，单位秒，默认值：`10`

`reload_delay_sec`：检测到文件变化后，触发插件重载前的延迟，单位秒，默认值：`1`

`blacklist`：一个字符串列表，包含会被该插件忽略的，插件文件夹中的文件名

## Command

`!!apr`: 显示帮助信息

`!!apr status`: 显示运行状态

`!!apr enable`: 启动插件自动重载器

`!!apr disable`: 关闭插件自动重载器

`!!apr set_interval <interval_sec>`: 设置检测间隔，单位：秒
