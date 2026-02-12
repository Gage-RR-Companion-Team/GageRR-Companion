1) make a data input window with three columns (one to distinguish the operator, one to distinguish the part number and one for the values from the measurement.) This should be able to be edited, with unlimited rows but only around 15 shown at a time, while the rest must be scrolled to. Add the ablilty to add columns for additional measurements to allow comparisons betweeen measurement methods. 
1.5) read a csv into a Pandas dataframe, make sure that all columns are labeled, there should be one column to specify the operator (this data can either be a number or a name to specify the operator) and one column to specify the part number (this will be an integer) and at least one column for the measurement values(this will be some number value, may be floating point). There should be mutiple measurement values for each operator-part combo, If there are mutiple methods being compared then therse should be additional measurement value columns (one for each measeurment method). If there is not one column for the operator or part number or value return an error stating that data is not in the correct structure
2) output window (shows total varience, operator varience and tool varience)
3) data visualization output (needs area on screen and code) (way to edit and change)
4) dropdown to pick which type of gage we're doing
5) documentation (user manual)
6) AI helper ???
7) authentification for data entry errors
8) export graphs and numbers, maybe use LLM for comentary
9) way to store data so they can come back to it
10) import/export data as a csv/df 