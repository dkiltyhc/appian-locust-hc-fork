from typing import Any, Dict, List

from .helper import extract_values, find_component_by_attribute_in_dict
from . import logger

log = logger.getLogger(__name__)


class GridInteractor:
    """
    Set of utility methods for interacting with grids, i.e. finding them, and manipulating them
    """

    def find_grid_by_label(self, label: str, form: Dict[str, Any]) -> Dict[str, Any]:
        grid = find_component_by_attribute_in_dict(attribute='label', value=label, component_tree=form)
        if not grid:
            raise Exception(f"Grid with label '{label}' not found in form")
        grid_type = grid['#t']
        if grid_type != 'GridField':
            raise Exception(f"Element found was not a Grid, was instead a {grid_type}")
        return grid

    def find_grid_by_index(self, index: int, form: Dict[str, Any]) -> Dict[str, Any]:
        grids = extract_values(form, '#t', "GridField")
        if not grids:
            raise Exception("No paging grids found in form")
        if len(grids) < index:
            raise Exception(f"Index {index} out of range, only found {len(grids)} grid(s) in form")
        return grids[index]

    def find_grid_by_label_or_index(self, form: Dict[str, Any], label: str = None, index: int = None) -> Dict[str, Any]:
        if label:
            grid = self.find_grid_by_label(label, form)
        elif index is not None:  # 0 is a valid index
            grid = self.find_grid_by_index(index, form)
        else:
            raise Exception("Either an index or a label must be passed")
        return grid

    def format_grid_display_label(self, grid: Dict[str, Any]) -> str:
        grid_label = str(grid.get("label")) if grid.get("label") else grid.get('_cId', "")[0:15]
        return grid_label

    def move_to_last_page(self, paging_grid: Dict[str, Any]) -> Dict[str, Any]:
        grid_data = self._get_grid_data(paging_grid)
        new_start_index = 1 + grid_data['total_count'] - grid_data['batch_size']
        grid_data['start_index'] = new_start_index
        return self._to_save_data(grid_data, paging_grid)

    def move_to_first_page(self, paging_grid: Dict[str, Any]) -> Dict[str, Any]:
        grid_data = self._get_grid_data(paging_grid)
        grid_data['start_index'] = 1
        return self._to_save_data(grid_data, paging_grid)

    def move_to_the_right(self, paging_grid: Dict[str, Any]) -> Dict[str, Any]:
        grid_data = self._get_grid_data(paging_grid)
        possible_new_index = grid_data['start_index'] + grid_data['batch_size']
        if grid_data['total_count'] < possible_new_index:
            log.warning(f"Cannot move to the right, index to move to {possible_new_index} is higher than total count {grid_data['total_count']}")
        else:
            grid_data['start_index'] = possible_new_index
        return self._to_save_data(grid_data, paging_grid)

    def move_to_the_left(self, paging_grid: Dict[str, Any]) -> Dict[str, Any]:
        grid_data = self._get_grid_data(paging_grid)
        possible_new_index = grid_data['start_index'] - grid_data['batch_size']
        if 0 >= possible_new_index:
            log.warning(f"Cannot move to the left, index to move to {possible_new_index} is less than or equal to 0")
        else:
            grid_data['start_index'] = possible_new_index
        return self._to_save_data(grid_data, paging_grid)

    def sort_grid(self, field_name: str, paging_grid: Dict[str, Any], ascending: bool = False) -> Dict[str, Any]:
        self.validate_sort(field_name, paging_grid)
        grid_data = self._get_grid_data(paging_grid)
        new_sort_info = self._get_sort_info(field_name, ascending)
        grid_data['sort_info'] = new_sort_info
        return self._to_save_data(grid_data, paging_grid)

    def validate_sort(self, field_name: str, paging_grid: Dict[str, Any]) -> None:
        possible_field_names = [col.get("field") for col in paging_grid.get("columns", [])]
        if field_name not in possible_field_names:
            raise Exception(f"Cannot sort, field '{field_name}' not found, fields were {possible_field_names}")

    def _get_sort_info(self, field_name: str, ascending: bool) -> List[Dict[str, Any]]:
        return [
            {
                "field": field_name,
                "ascending": ascending
            }
        ]

    def _get_grid_data(self, paging_grid: Dict[str, Any]) -> Dict[str, Any]:
        # Support grid component with paging info within value.pagingInfo
        grid_value = paging_grid.get("value", "")
        paging_info = grid_value.get("pagingInfo", "") or paging_grid['value']
        total_count = int(paging_grid['totalCount'])
        start_index = int(paging_info['startIndex'])
        batch_size = int(paging_info['batchSize'])
        sort_info = paging_info['sort']

        return {
            'total_count': total_count,
            'start_index': start_index,
            'batch_size': batch_size,
            'sort_info': sort_info
        }

    def _to_save_data(self, grid_data: Dict[str, Any], paging_grid: Dict[str, Any]) -> Dict[str, Any]:
        start_index = grid_data['start_index']
        batch_size = grid_data['batch_size']
        sort_info = grid_data['sort_info']

        # Support grid component with paging info within value.pagingInfo
        grid_value = paging_grid.get("value", "")
        if "pagingInfo" not in grid_value:
            # No pagingInfo element between value and paging data
            return {
                "startIndex": start_index,
                "batchSize": batch_size,
                "sort": sort_info,
                "#t": "PagingInfo"
            }
        else:
            # Maintain pagingInfo in updated state
            return {
                "#t": "GridSelection",
                'pagingInfo': {
                    "startIndex": start_index,
                    "batchSize": batch_size,
                    "sort": sort_info
                }
            }
