"""
File: manager/excel.py
Author: Jeremiah Nairn

Description: Holds all of the functionality for making excel files and displaying them as images
"""

#import libraries
import openpyxl as xl
import win32com.client as win32
import os

#class to manage the excel file
class ExcelManager:

    #constructor
    def __init__(self,filename,playerdata,rounds,total_players):
        #important variables
        self.workbook = xl.Workbook()
        self.sheet = self.workbook.active
        self.filename = filename
        self.rounds = rounds
        self.draft_data = playerdata
        self.total_players = total_players
        #create two sheets, one for the draft, and one for the results
        self.sheet.title = "Draft"
        self.workbook.create_sheet(title="Results")
        #define styles
        self.header_fill = xl.styles.PatternFill("solid", fgColor="0F243E")  #dark blue
        self.header_font = xl.styles.Font(color="FFFFFF", bold=True, size=12)
        self.body_fill = xl.styles.PatternFill("solid", fgColor="0c0a0f")  #almost black
        self.body_font = xl.styles.Font(color="FFFFFF", bold=False, size=12)
        self.alignment = xl.styles.Alignment(horizontal="center", vertical="center")
        self.all_border = xl.styles.Border(
            left=xl.styles.Side(style="thin",color="FFFFFF"), right=xl.styles.Side(style="thin",color="FFFFFF"),
            top=xl.styles.Side(style="thin",color="FFFFFF"), bottom=xl.styles.Side(style="thin",color="FFFFFF"),
        )
        self.side_borders = xl.styles.Border(
            left=xl.styles.Side(style="thin",color="FFFFFF"), right=xl.styles.Side(style="thin",color="FFFFFF")
        )
        return

    #function to save the excel file
    def save_excel(self):
        #locate the excels folder
        if not os.path.exists('excels'):
            os.makedirs('excels')
        #save the file
        self.workbook.save(f"excels/{self.filename}.xlsx")
        print(f"[EXCEL] Excel file saved as {f"{self.filename}.xlsx"}")

    def update_playerdata(self,playerdata):
        #clear the current playerdata
        self.draft_data = playerdata

    #function to create the draft sheet
    def create_draft_sheet(self):
        #create the header
        self.sheet["A1"] = "Drafter"
        self.sheet["A1"].font = self.header_font
        self.sheet["A1"].fill = self.header_fill
        self.sheet["A1"].border = self.all_border
        self.sheet["A1"].alignment = self.alignment
        self.sheet.column_dimensions['A'].width = 30
        #create the round headers
        for round in range(self.rounds):
            col = chr(66 + round)  # ASCII value for 'B' is 66
            cell = f"{col}1"
            self.sheet[cell] = f"Pick {round + 1}"
            self.sheet[cell].font = self.header_font
            self.sheet[cell].fill = self.header_fill
            self.sheet[cell].border = self.all_border
            self.sheet[cell].alignment = self.alignment
            self.sheet.column_dimensions[col].width = 15
        #get the position of each player, and format each collumn
        for player in range(self.total_players):
            row = player + 2  # Starting from row 2 since row 1 is the header
            drafter_cell = f"A{row}"
            #identify the player by their draft position
            for drafter in self.draft_data:
                if drafter['position'] == player:
                    self.sheet[drafter_cell] = drafter['name']
            #format the cells in the row
            for round in range(self.rounds+1):
                col = chr(65 + round)
                pick_cell = f"{col}{row}"
                self.sheet[pick_cell].border = self.side_borders
                self.sheet[pick_cell].alignment = self.alignment
                self.sheet[pick_cell].font = self.body_font
                self.sheet[pick_cell].fill = self.body_fill

        #save the file and return
        self.save_excel()
        return

    #function to fill in the draft sheet with data
    def fill_draft_sheet(self, draft_data):

        #save the file and return
        self.save_excel()
        return

    #function to get the draft as an image
    def get_draft_as_image(self):
        # open the excel file using win32com
        excel = win32.Dispatch("Excel.Application")
        excel.Visible = False
        wb_path = os.path.abspath(f"excels/{self.filename}.xlsx")
        wb = excel.Workbooks.Open(wb_path)
        ws = wb.Sheets("Draft")
        # copy the used range as an image and paste it
        used_range = ws.UsedRange
        used_range.CopyPicture(Format=2)
        #create a temporary ChartObject, paste the picture into it, export the chart as an image, then delete it
        chart_object = ws.ChartObjects().Add(0, 0, used_range.Width, used_range.Height)
        chart = chart_object.Chart
        chart.Paste()
        # ensure manager/excels directory exists and save the picture there
        base_dir = os.path.dirname(os.path.abspath(__file__))  # manager folder
        export_dir = os.path.join(base_dir, "excels")
        os.makedirs(export_dir, exist_ok=True)
        image_path = os.path.join(export_dir, f"{self.filename}_draft.png")
        # Export the chart as an image (use FilterName="PNG" to ensure PNG format)
        try:
            chart.Export(image_path, FilterName="PNG")
        except TypeError:
            # some COM implementations accept only positional args
            chart.Export(image_path, "PNG")
        # remove the temporary chart object
        chart_object.Delete()
        print(f"[EXCEL] Draft image saved as {image_path}")
        # close the workbook and quit excel
        wb.Close(SaveChanges=False)
        excel.Quit()
        return image_path

        

    #function to create the results sheet
    def create_results_sheet(self):

        #save the file and return
        self.save_excel()
        return

    #function to fill in the results sheet with data
    def fill_results_sheet(self, draft_data, results_data):

        #save the file and return
        self.save_excel()
        return

    #function to get the results
    def get_results_as_image(self):
        return

#function to wipe the excel folder
def wipe_excel_folder():
    #delete all xlsx files in the excels folder
    for file in os.listdir('excels'):
        if file.endswith('.xlsx'):
            os.remove(os.path.join('excels', file))
    return
