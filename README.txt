This is the code repository for the Master Thesis "Who cares? An optimization-simulation approach to the Home Care Problem".

The code is structured as follows:
- the src/ folder contains all the source code for both the optimization and the simulation models;
- the scripts/ folder contains the bash script that converts the output of the solver in a JSON via text manipulation;
- the opt-data/ folder contains the dataset that has been used in the testing phase of the optimizer;
- the sim-data/ folder contains the dataset that has been used in the testing phase of the simulator;
- the model/ folder contains the optimization model in AMPL, with the .mod, .dat, and .ops files required by the IBM optimizer;
- the data/ folder contains the model currently in use.

To use the code, generate a .ipynb file in the main repository and run any desired function.
Main elements of the repository:
- execute_test(), in src/processing.py, to generate a new instance and run the optimizer;
- the Patient, Operator, Visit, Manager, and HCModel classes, in src/simulator.py, responsible for the simulation part;
- the constants, in src/constants.py.