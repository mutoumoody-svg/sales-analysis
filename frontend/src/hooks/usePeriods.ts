import { useEffect, useState, useCallback } from 'react';
import { salesApi } from '../api';

export interface PeriodOption {
  period: string;
  row_count: number;
  net_revenue: number;
}

/**
 * 月份选择器 Hook
 * 自动获取可用月份列表，管理选中状态
 * 返回: { periods, month, setMonth, loading }
 */
export function usePeriods() {
  const [periods, setPeriods] = useState<PeriodOption[]>([]);
  const [month, setMonth] = useState<string>('');
  const [loading, setLoading] = useState(true);

  const fetchPeriods = useCallback(async () => {
    try {
      const resp = await salesApi.periods();
      const data = resp.data?.data || [];
      setPeriods(data);
      // 默认选最新月份（第一个，已按降序排列）
      if (data.length > 0 && !month) {
        setMonth(data[0].period);
      }
    } catch (e) {
      console.error('Failed to fetch periods:', e);
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => {
    fetchPeriods();
  }, [fetchPeriods]);

  return { periods, month, setMonth, loading };
}
