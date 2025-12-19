/**
 * Credit Engine 2.0 - Filter Store
 * Shared filter state for violations across components
 */
import { create } from 'zustand';

export const useFilterStore = create((set) => ({
  // Filter selections
  filters: {
    bureaus: [],
    severities: [],
    categories: [],
    accounts: [],
  },

  // Search term for account/creditor name search
  searchTerm: '',

  // Set search term
  setSearchTerm: (term) => set({ searchTerm: term }),

  // Toggle a filter value
  toggleFilter: (type, value) => set((state) => {
    const currentList = state.filters[type];
    const newList = currentList.includes(value)
      ? currentList.filter((item) => item !== value)
      : [...currentList, value];
    return { filters: { ...state.filters, [type]: newList } };
  }),

  // Clear all filters (including search)
  clearFilters: () => set({
    filters: { bureaus: [], severities: [], categories: [], accounts: [] },
    searchTerm: '',
  }),

  // Check if any filters active
  hasActiveFilters: (state) => {
    return state.filters.bureaus.length > 0 ||
           state.filters.severities.length > 0 ||
           state.filters.categories.length > 0 ||
           state.filters.accounts.length > 0;
  },
}));
