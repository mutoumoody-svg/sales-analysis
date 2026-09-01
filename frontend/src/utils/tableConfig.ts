import type { TablePaginationConfig } from 'antd';

/**
 * 标准分页配置：每页 10/20/50/100 条可选
 * 使用 defaultPageSize（非受控初始值），让 AntD 内部管理 pageSize。
 * 若用 pageSize（受控），每次渲染传新对象时会和内部状态冲突，
 * 导致用户选择 50 条后又被 prop 的 pageSize:20 拉回去，下拉变成"不能用"。
 */
export const standardPagination = (pageSize = 20): TablePaginationConfig => ({
  defaultPageSize: pageSize,
  showSizeChanger: true,
  showTotal: (t: number) => `共 ${t} 条`,
  pageSizeOptions: ['10', '20', '50', '100'],
});

/**
 * 通用字符串排序函数
 */
export const stringSorter = <T extends Record<string, unknown>>(field: keyof T) =>
  (a: T, b: T) => String(a[field] ?? '').localeCompare(String(b[field] ?? ''));

/**
 * 通用数值排序函数
 */
export const numberSorter = <T extends Record<string, unknown>>(field: keyof T) =>
  (a: T, b: T) => {
    const av = a[field] as number | null | undefined;
    const bv = b[field] as number | null | undefined;
    if (av == null && bv == null) return 0;
    if (av == null) return -1;
    if (bv == null) return 1;
    return (av as number) - (bv as number);
  };
