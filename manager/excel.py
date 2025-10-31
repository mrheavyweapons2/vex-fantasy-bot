"""
File: manager/excel.py
Author: Jeremiah Nairn

Description: Holds all of the functionality for making excel files and displaying them as images
"""

#import libraries
import openpyxl as xl

#class to manage the excel file
class ExcelManager:

    #get the save directory
    

    #constructor
    def __init__(self,filename):
        #variables
        self.workbook = xl.Workbook()
        self.sheet = self.workbook.active
        self.filename = filename
        #create two sheets, one for the draft, and one for the results
        self.sheet.title = "Draft"
        self.workbook.create_sheet(title="Results")
        #define styles
        self.header_fill = xl.styles.PatternFill("solid", fgColor="191970")  # dark blue background
        self.header_font = xl.styles.Font(color="FFFFFF", bold=True, size=12)
        self.title_font = xl.styles.Font(bold=True, size=14)
        self.all_borders = xl.styles.Border(
            left=xl.styles.Side(style="thin"), right=xl.styles.Side(style="thin"),
            top=xl.styles.Side(style="thin"), bottom=xl.styles.Side(style="thin")
        )
        self.side_borders = xl.styles.Border(
            left=xl.styles.Side(style="thin"), right=xl.styles.Side(style="thin")
        )
        return

    #function to save the excel file
    def save_excel(self):
        self.workbook.save(f"{self.filename}.xlsx")
        print(f"[EXCEL] Excel file saved as {f"{self.filename}.xlsx"}")

    #function to create the draft sheet
    def create_draft_sheet(self):

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
        return

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
    return

#test code
if __name__ == "__main__":
    excel_manager = ExcelManager("test_draft")
    excel_manager.create_draft_sheet()
    excel_manager.fill_draft_sheet(draft_data=[])