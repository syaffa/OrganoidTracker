from typing import Dict, Any, Optional, Union

from organoid_tracker.comparison.report import ComparisonReport, Category
from organoid_tracker.core import UserError, COLOR_CELL_CURRENT
from organoid_tracker.core.position import Position
from organoid_tracker.gui import dialog
from organoid_tracker.gui.dialog import DefaultOption
from organoid_tracker.text_popup.text_popup import RichTextPopup
from organoid_tracker.gui.window import Window
from organoid_tracker.visualizer import activate
from organoid_tracker.visualizer.exitable_image_visualizer import ExitableImageVisualizer

_MAX_COUNT = 50


def get_menu_items(window: Window) -> Dict[str, Any]:
    return {
         "Tools//Report-View comparison report...": lambda: _open_comparison_report(window),
    }


def _open_comparison_report(window: Window):
    file = dialog.prompt_load_file("Open a comparison report...", [("Comparison repots", "*.json")])
    if file is None:
        return

    from organoid_tracker.comparison import report_json_io
    report = report_json_io.load_report(file)
    _popup_comparison_report(window, report)


class _ComparisonVisualizer(ExitableImageVisualizer):

    _report: ComparisonReport
    _category: Category

    def __init__(self, window: Window, report: ComparisonReport, category: Category):
        super().__init__(window)
        self._report = report
        self._category = category

    def _get_figure_title(self) -> str:
        return self._report.title + ": " + self._category.name + "\n" + super()._get_figure_title()

    def _draw_extra(self):
        for position in self._report.get_positions(self._category, time_point=self._time_point):
            if abs(position.z - self._z) > self.MAX_Z_DISTANCE:
                continue
            self._draw_selection(position, COLOR_CELL_CURRENT)


class _ComparisonTextPopup(RichTextPopup):
    """Text-based overview of the report."""

    _window: Window  # The main window
    _report: ComparisonReport

    def __init__(self, window: Window, report: ComparisonReport):
        self._window = window
        self._report = report

    def get_title(self) -> str:
        return self._report.title

    def navigate(self, url: str) -> Optional[str]:
        if url == RichTextPopup.INDEX:
            return self._main_page()
        if url.startswith("category/"):
            category = Category(url[len("category/"):])
            if self._report.count_positions(category) == 0:
                raise UserError("No entries found", f"The report contains no entries for \"{category.name}\".")
            return self._category_page(category)
        if url.startswith("visualize_category/"):
            category = Category(url[len("visualize_category/"):])
            if self._report.count_positions(category) == 0:
                raise UserError("No entries found", f"The report contains no entries for \"{category.name}\".")
            activate(_ComparisonVisualizer(self._window, self._report, category))
            return None
        if url.startswith("position/"):
            _, position_str = url.split("/")
            self._window.get_gui_experiment().goto_position(_parse_position(position_str))
            return None
        if url.startswith("edit_position/"):
            _, category_str, position_str = url.split("/")
            category = self._report.get_category_by_name(category_str)
            position = _parse_position(position_str)
            return self._edit_position_page(category, position)
        if url.startswith("move_position/"):
            _, old_category_str, position_str, new_category_str = url.split("/")
            old_category = self._report.get_category_by_name(old_category_str)
            position = _parse_position(position_str)
            new_category = self._report.get_category_by_name(new_category_str)
            self._report.delete_data(old_category, position)
            self._report.add_data(new_category, position)
            dialog.popup_message("Position moved", f"Position is now in {new_category.name}.")
            return self._category_page(old_category)
        if url.startswith("delete_position/"):
            _, old_category_str, position_str = url.split("/")
            old_category = self._report.get_category_by_name(old_category_str)
            position = _parse_position(position_str)
            if dialog.prompt_options("Position deleted", f"Deleted the position from {old_category.name}.",
                                     option_1="Undo", option_default=DefaultOption.OK) != 1:
                # Only delete if the user didn't press Undo
                self._report.delete_data(old_category, position)
            return self._category_page(old_category)
        if url == "save_json":
            save_file = dialog.prompt_save_file("Save the comparison result", [("JSON files", "*.json")])
            if save_file is not None:
                from organoid_tracker.comparison import report_json_io
                report_json_io.save_report(self._report, save_file)
            return None
        if url == "save_time_csv":
            save_file = dialog.prompt_save_file("Save the comparison result", [("CSV files", "*.csv")])
            if save_file is not None:
                from organoid_tracker.comparison import report_csv_io
                report_csv_io.save_report_time_statistics(self._report, save_file)
            return None
        return None

    def _main_page(self) -> str:
        categories = self._report.get_categories()

        text = f"# {self._report.title}\n"
        if len(self._report.summary) > 0:
            text += f"{self._report.summary}\n"
        recorded_parameters = dict(self._report.recorded_parameters())
        if len(recorded_parameters) > 0:
            text += "\n"
            for parameter_name, parameter_value in self._report.recorded_parameters():
                text += f"    {parameter_name} = {parameter_value}\n"
            text += "\n"

        for category in categories:
            text += f"* {category.name} ({self._report.count_positions(category)} entries) [View](category/{category.name}) \n"
        text += "\n[Save the report](save_json) - [Export as CSV](save_time_csv)"
        return text

    def _category_page(self, category: Category) -> str:
        """Renders the category page, which shows a list of all positions."""
        text = "# " + category.name + "\n\n[← Back to main page](" + RichTextPopup.INDEX + ")\n\n"
        text += f"[Highlight positions](visualize_category/{category.name})\n"

        count = 0
        for position, details in self._report.get_entries(category):
            count += 1
            if count > _MAX_COUNT:
                text += "\n*  ...and " + str(self._report.count_positions(category) - _MAX_COUNT) + " more."
                return text
            text += "\n* "
            text += _markdown(position)
            for detail in details.details:
                text += " "
                text += _markdown(detail)
            text += f" [Edit](edit_position/{category.name}/{_x_y_z_t(position)})"
        return text

    def _edit_position_page(self, category: Category, position: Position) -> str:
        text = f"# Editing position in {category.name}" \
               f"\n\n*{position}*\n[Show in image viewer](position/{_x_y_z_t(position)}).\n"
        for some_category in self._report.get_categories():
            if some_category == category:
                continue
            text += f"\n* [Move to {some_category.name}](move_position/{category.name}/{_x_y_z_t(position)}/{some_category.name})"
        text += f"\n* [Delete position](delete_position/{category.name}/{_x_y_z_t(position)})"

        text += f"\n\n[Cancel](category/{category.name})"
        return text


def _parse_position(position_str: str) -> Position:
    """Parses "1.4 5.5 3 7" into `Position(1.4, 5.5, 3, time_point_number=7)`. See also _x_y_z_t(pos)"""
    x, y, z, t = position_str.split(" ")
    return Position(float(x), float(y), float(z), time_point_number=int(t))


def _markdown(value: Union[Position, str]) -> str:
    if isinstance(value, Position):
        return "[" + str(value) + f"](position/{_x_y_z_t(value)})"
    return value


def _x_y_z_t(position: Position) -> str:
    """Returns the position as a string that can be parsed by _parse_position(str)."""
    return f"{position.x} {position.y} {position.z} {position.time_point_number()}"


def _popup_comparison_report(window: Window, report: ComparisonReport):
    dialog.popup_rich_text(_ComparisonTextPopup(window, report))
