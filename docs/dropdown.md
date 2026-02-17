Name: 

dropdown

What it does: 

The dropdown menu is a GUI component where the user is able to select the type of gage testing that they wish to complete. 
The list will include: Crossed Gage R&R, Nested Gage R&R, Expanded Gage R&R, and Type-1 Gage Testing. 

After selecting from the menu, there should be an adjacent text box that gives a high-level overview of the type of testing the user selected. 

The user can confirm the selection by interacting with a confirmation button, and after doing so it will bring the user to the downstream Gage R&R input component.

Inputs: 

The only inputs for the dropdown menu are user inputs. 
The user will interact with the dropdown menu to select the type of testing they wish to do from the list of inputs. 
After doing so, the user will interact with a confirmation button to complete the selection.
There will also be a red X button to allow the user to leave the dropdown, and return to the GUI's previous instance.

Outputs: 

This will output a string from a list that corresponds to the type of testing selected. 
The list of outputs is defined as the following [crossed, nested, expanded, type1] where each element in the provided list is a string.

How it uses other components: 

The dropdown component will be accessed by an upstream GUI component to initiate its use. 
The dropdown will also call upon the documentation to provide a high-level overview of the type of testing the user selected. 
The dropdown outputs will be used by components such as the data_input_window, data_output_window, and the data_visualization_output

Side effects:

After successfully completing, downstream use cases for the data_input_window will be accessible to the user. 

How it should be made:

The dropdown component should be made in Python using the Streamlit library to build the GUI. 