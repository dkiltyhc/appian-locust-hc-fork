import json
import unittest
from copy import deepcopy
from appian_locust._grid_interactor import GridInteractor
from .mock_reader import read_mock_file_as_dict


class TestGridInteractor(unittest.TestCase):
    grid_interactor: GridInteractor = GridInteractor()
    grid_form_orig = read_mock_file_as_dict("report_with_rep_sales_grid.json")

    def setUp(self) -> None:
        self.grid_form = deepcopy(self.grid_form_orig)

    def test_find_grid_by_label_success(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        grid = self.grid_interactor.find_grid_by_label(form_label, self.grid_form)
        self.assertEqual(grid['label'], form_label)

    def test_find_grid_by_label_missing(self) -> None:
        form_label = 'Topest Sales Reps by Total Sales'
        with self.assertRaisesRegex(Exception, f"Grid with label '{form_label}'"):
            grid = self.grid_interactor.find_grid_by_label(form_label, self.grid_form)

    def test_find_grid_by_index(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        grid = self.grid_interactor.find_grid_by_index(0, self.grid_form)
        self.assertEqual(grid['label'], form_label)

    def test_find_grid_by_index_out_of_range(self) -> None:
        with self.assertRaisesRegex(Exception, 'Index 5 out of range'):
            grid = self.grid_interactor.find_grid_by_index(5, self.grid_form)

    def test_find_grid_no_grids_found(self) -> None:
        with self.assertRaisesRegex(Exception, 'No paging grids found in form'):
            grid = self.grid_interactor.find_grid_by_index(5, {})

    def test_find_grid_by_label_different(self) -> None:
        form_label = 'Orders & Sales Reps Performance'
        with self.assertRaisesRegex(Exception, "Element found was not a Grid"):
            grid = self.grid_interactor.find_grid_by_label(form_label, self.grid_form)

    def test_move_to_end_and_beginning(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        grid = self.grid_interactor.find_grid_by_label(form_label, self.grid_form)

        end_save_value = self.grid_interactor.move_to_last_page(grid)
        self.assertEqual(91, end_save_value['startIndex'])

        # Now at the end
        grid['value'] = end_save_value

        beginning_save_value = self.grid_interactor.move_to_first_page(grid)
        self.assertEqual(1, beginning_save_value['startIndex'])

    def test_move_to_right_left_boundaries(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        grid = self.grid_interactor.find_grid_by_label(form_label, self.grid_form)

        beginning_save_value = self.grid_interactor.move_to_the_left(grid)
        self.assertEqual(1, beginning_save_value['startIndex'])

        # Now at the end
        grid['value']['startIndex'] = 91

        beginning_save_value = self.grid_interactor.move_to_the_right(grid)
        self.assertEqual(91, beginning_save_value['startIndex'])

    def test_move_to_right_and_left(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        grid = self.grid_interactor.find_grid_by_label(form_label, self.grid_form)

        save_value = self.grid_interactor.move_to_the_right(grid)
        self.assertEqual(11, save_value['startIndex'])

        grid['value'] = save_value

        save_value = self.grid_interactor.move_to_the_left(grid)
        self.assertEqual(1, save_value['startIndex'])

    def test_sort_ascending_and_descending_error(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        grid = self.grid_interactor.find_grid_by_label(form_label, self.grid_form)
        with self.assertRaisesRegex(Exception, "Cannot sort, field 'fake' not found"):
            self.grid_interactor.sort_grid(field_name='fake', paging_grid=grid)

    def test_sort_ascending_and_descending(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        grid = self.grid_interactor.find_grid_by_label(form_label, self.grid_form)
        sort_save = self.grid_interactor.sort_grid(field_name='Total', ascending=True, paging_grid=grid)

        self.assertEqual(sort_save['sort'][0]['field'], 'Total')
        self.assertEqual(sort_save['sort'][0]['ascending'], True)

        sort_save = self.grid_interactor.sort_grid(field_name='AccountOwner', ascending=False, paging_grid=grid)

        self.assertEqual(sort_save['sort'][0]['field'], 'AccountOwner')
        self.assertEqual(sort_save['sort'][0]['ascending'], False)


if __name__ == '__main__':
    unittest.main()
