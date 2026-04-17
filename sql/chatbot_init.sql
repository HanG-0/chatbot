-- 创建数据库
CREATE DATABASE IF NOT EXISTS `chatbot` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `chatbot`;

-- --------------------------------------------------------
-- 表结构：user_info (用户信息及案件信息表)
-- 根据代码中 selected_columns = [0, 8, 5, 9, 10, 6, 11, 4] 以及对应的中文释义推断
-- --------------------------------------------------------
DROP TABLE IF EXISTS `user_info`;
CREATE TABLE `user_info` (
  `name` varchar(255) NOT NULL COMMENT '索引0: 当事人信息(姓名)',
  `account` varchar(255) NOT NULL UNIQUE COMMENT '索引1: 登录用户名',
  `password` varchar(255) NOT NULL COMMENT '索引2: 登录密码',
  `phone` varchar(50) DEFAULT NULL COMMENT '索引3: 预留字段(如手机号)',
  `total_debt` decimal(10,2) DEFAULT '0.00' COMMENT '索引4: 总欠款',
  `debt_project` varchar(255) DEFAULT NULL COMMENT '索引5: 欠款项目(如某某银行)',
  `overdue_days` int(11) DEFAULT '0' COMMENT '索引6: 逾期天数',
  `id_card` varchar(50) DEFAULT NULL COMMENT '索引7: 预留字段(如身份证号)',
  `debt_reason` varchar(500) DEFAULT NULL COMMENT '索引8: 欠款原因',
  `loan_amount` decimal(10,2) DEFAULT '0.00' COMMENT '索引9: 欠款金额(贷款本金)',
  `total_interest` decimal(10,2) DEFAULT '0.00' COMMENT '索引10: 总利息',
  `total_penalty` decimal(10,2) DEFAULT '0.00' COMMENT '索引11: 总罚息',
  PRIMARY KEY (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息及案件表';

-- --------------------------------------------------------
-- 插入测试数据
-- --------------------------------------------------------
INSERT INTO `user_info` (`name`, `account`, `password`, `total_debt`, `debt_project`, `overdue_days`, `debt_reason`, `loan_amount`, `total_interest`, `total_penalty`) VALUES
    ('张三', 'zhangsan', '123456', 15500.00, '招商银行', 45, '生意失败资金周转困难', 15000.00, 300.00, 200.00);


-- --------------------------------------------------------
-- 表结构：mediation_record (调解记录表)
-- 根据代码 save_db() 函数推断
-- --------------------------------------------------------
DROP TABLE IF EXISTS `mediation_record`;
CREATE TABLE `mediation_record` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `user_id` varchar(255) NOT NULL COMMENT '用户名',
  `content` longtext NOT NULL COMMENT '对话内容JSON字符串',
  `is_success` tinyint(1) DEFAULT '0' COMMENT '预测是否成功',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='调解对话记录表';



-- 还款计划进度表
create table repayment_plan
(
    id                  int auto_increment comment '自增主键'
        primary key,
    user_id             varchar(255)                          not null comment '用户名',
    repayment_plan      text                                  not null comment '具体调解方案，文本形式',
    down_payment_amount decimal(10, 2)                        null comment '首付金额',
    installment_count   int                                   null comment '分期数量，可选',
    installment_amount  decimal(10, 2)                        null comment '每期还款金额，可选',
    status              varchar(50) default 'pending_sign'    null comment '状态：pending_sign-待签署，signed-已签署，archived-已归档',
    contract_file       varchar(500)                          null comment '协议文件路径',
    signature_image     varchar(500)                          null comment '签名图片路径',
    created_at          timestamp   default CURRENT_TIMESTAMP not null comment '记录创建时间',
    updated_at          timestamp   default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '记录更新时间'
)
    comment '还款计划表';

create index idx_status
    on repayment_plan (status);

create index idx_user_id
    on repayment_plan (user_id);


-- 调解案件进度表
create table mediation_case_progress
(
    id            int auto_increment comment '自增主键'
        primary key,
    user_id       varchar(255)                          not null comment '用户名',
    status        varchar(20) default 'S0'              not null comment '当前状态：S0(初始)/S1(了解情况)/S2(协商中，了解意愿)/S3(减免)/S4(分期还款)/S5(达成协议)/S6(调解失败)',
    contract_file varchar(500)                          null comment '合同文件路径',
    image_file    varchar(128)                          null comment '签名图片保存路径 AFTER',
    created_at    timestamp   default CURRENT_TIMESTAMP not null comment '记录创建时间',
    updated_at    timestamp   default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '记录更新时间'
)
    comment '调解案件进度表';

create index idx_status
    on mediation_case_progress (status);

create index idx_user_id
    on mediation_case_progress (user_id);


