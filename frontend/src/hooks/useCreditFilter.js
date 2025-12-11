/**
 * Credit Engine 2.0 - Universal Filtering Hook
 * "SQL Engine in JavaScript" - Slices violations by Bureau/Severity/Category
 * Uses shared Zustand store for filter state sync across components
 */
import { useMemo } from 'react';
import { useFilterStore } from '../state';

export function useCreditFilter(allViolations) {
  // Use shared filter store instead of local state
  const { filters, toggleFilter, clearFilters } = useFilterStore();

  // The "Join" Logic - only runs when filters or data change
  const filteredData = useMemo(() => {
    if (!allViolations || allViolations.length === 0) {
      return [];
    }

    return allViolations.filter((violation) => {
      // 1. Bureau Slice
      if (filters.bureaus.length > 0 && !filters.bureaus.includes(violation.bureau)) {
        return false;
      }

      // 2. Severity Slice
      if (filters.severities.length > 0 && !filters.severities.includes(violation.severity)) {
        return false;
      }

      // 3. Category Slice (using violation.violation_type)
      if (filters.categories.length > 0 && !filters.categories.includes(violation.violation_type)) {
        return false;
      }

      return true; // Passed all checks
    });
  }, [allViolations, filters]);

  // Extract unique values from data for dynamic filter options
  const filterOptions = useMemo(() => {
    if (!allViolations || allViolations.length === 0) {
      return { bureaus: [], severities: [], categories: [] };
    }

    const bureaus = [...new Set(allViolations.map(v => v.bureau).filter(Boolean))];
    const severities = [...new Set(allViolations.map(v => v.severity).filter(Boolean))];
    const categories = [...new Set(allViolations.map(v => v.violation_type).filter(Boolean))];

    return { bureaus, severities, categories };
  }, [allViolations]);

  // Check if any filters are active
  const hasActiveFilters = filters.bureaus.length > 0 ||
                           filters.severities.length > 0 ||
                           filters.categories.length > 0;

  return {
    filteredData,
    filters,
    filterOptions,
    toggleFilter,
    clearFilters,
    hasActiveFilters,
    totalCount: allViolations?.length || 0,
    filteredCount: filteredData.length
  };
}
