
import pandas as pd

def convert_action_columns(actions):
    actions['Realized P/L'] = pd.to_numeric(actions['Realized P/L'], errors='coerce')
    actions['Proceeds'] = pd.to_numeric(actions['Proceeds'], errors='coerce')
    actions['Value'] = pd.to_numeric(actions['Value'], errors='coerce')
    actions['Quantity'] = pd.to_numeric(actions['Quantity'], errors='coerce')
    actions['Date/Time'] = pd.to_datetime(actions['Date/Time'])
    actions['Category'] = 'Actions'
    actions = actions[['Category'] + [col for col in actions.columns if col != 'Category']]
    return actions
    