from riscemv.ReservationStations import ReservationStations
from riscemv.RegisterFile import RegisterFile
from riscemv.RegisterStatus import RegisterStatus
from riscemv.InstructionBuffer import InstructionBuffer
from riscemv.DataMemory import DataMemory

from riscemv.ISA.RType_Instruction import RType_Instruction
from riscemv.ISA.IType_Instruction import IType_Instruction
from riscemv.ISA.SType_Instruction import SType_Instruction
from riscemv.ISA.BType_Instruction import BType_Instruction


class Tomasulo:
    def __init__(self, XLEN, thread_id, adders_number, multipliers_number, dividers_number, loaders_number, fp_adders_number, fp_multipliers_number, fp_dividers_number, fp_loaders_number):
        self.__steps = 0
        self.stall = False
        self.thread_id = thread_id

        self.IFQ = InstructionBuffer()
        self.Regs = RegisterFile()
        self.RegisterStat = RegisterStatus()
        self.RS = ReservationStations(adders_number, multipliers_number, dividers_number, loaders_number, fp_adders_number, fp_multipliers_number, fp_dividers_number, fp_loaders_number)
        self.DM = DataMemory(1*1024)  # 1 Kb


    def step(self):
        self.__steps += 1
        print("[TOM] Performing step number", self.__steps)

        self.write()
        self.execute() # order is inverted to avoid skipping steps
        self.issue()

        return self.__steps


    def reset_steps(self):
        self.__steps = 0


    def issue(self):
        pc = self.Regs.PC.get_value()

        if self.stall:
            print("[TOM] self.stall = True, not issuing anything")
        elif self.IFQ.empty(pc):
            print("[TOM] IFQ is empty")
        else:
            ifq_entry = self.IFQ.get(pc)
            instruction = ifq_entry.instruction
            self.Regs.IR.set_value(int(instruction.to_binary(), 2))
            self.IFQ.set_instruction_issue(pc, self.__steps)
            print("[TOM] Issuing", instruction)

            if isinstance(instruction, BType_Instruction):
                self.stall = True

            fu = self.RS.get_first_free(instruction.functional_unit, self.thread_id)

            if fu is None:
                print("No available Reservation Station, stalling")
            else:
                pc += 4
                self.Regs.PC.set_value(pc)
                fu.instruction = instruction
                fu.time_remaining = instruction.clock_needed

                if isinstance(instruction, RType_Instruction) or isinstance(instruction, BType_Instruction):
                    if self.RegisterStat.get_status(instruction.rs1, instruction.rs1_type) is not None:
                        fu.Qj = self.RegisterStat.get_status(instruction.rs1, instruction.rs1_type)
                    else:
                        fu.Vj = self.Regs.read(instruction.rs1, instruction.rs1_type)
                        fu.Qj = 0
                    if self.RegisterStat.get_status(instruction.rs2, instruction.rs2_type) is not None:
                        fu.Qk = self.RegisterStat.get_status(instruction.rs2, instruction.rs2_type)
                    else:
                        fu.Vk = self.Regs.read(instruction.rs2, instruction.rs2_type)
                        fu.Qk = 0
                elif isinstance(instruction, IType_Instruction):
                    if self.RegisterStat.get_status(instruction.rs, instruction.rs_type) is not None:
                        fu.Qj = self.RegisterStat.get_status(instruction.rs, instruction.rs_type)
                    else:
                        fu.Vj = self.Regs.read(instruction.rs, instruction.rs_type)
                        fu.Qj = 0
                    fu.A = instruction.imm # store the immediate value
                    fu.Qk = 0
                elif isinstance(instruction, SType_Instruction):
                    if self.RegisterStat.get_status(instruction.rs1, instruction.rs1_type) is not None:
                        fu.Qj = self.RegisterStat.get_status(instruction.rs1, instruction.rs1_type)
                    else:
                        fu.Vj = self.Regs.read(instruction.rs1, instruction.rs1_type)
                        fu.Qj = 0
                    fu.A = instruction.imm # store the immediate value
                    fu.Qk = 0
                    if self.RegisterStat.get_status(instruction.rs2, instruction.rs2_type) is not None:
                        fu.Qk = self.RegisterStat.get_status(instruction.rs2, instruction.rs2_type)
                    else:
                        fu.Vk = self.Regs.read(instruction.rs2, instruction.rs2_type)
                        fu.Qk = 0

                if not isinstance(instruction, SType_Instruction) and not isinstance(instruction, BType_Instruction):
                    self.RegisterStat.add_status(instruction.rd, fu.name, instruction.rd_type)


    def execute(self):
        for fu in self.RS.get_fus_of_thread(self.thread_id):
            if fu.busy and fu.time_remaining > 0 and fu.Qj == 0 and fu.Qk == 0:
                self.IFQ.set_instruction_execute(fu.instruction.program_counter, self.__steps)
                fu.time_remaining -= 1

                if fu.time_remaining == 1 and isinstance(fu.instruction, IType_Instruction):
                    if fu.instruction.is_load():
                        fu.A = fu.instruction.execute(fu.Vj) # load first clock cycle
                elif fu.time_remaining == 0:
                    if isinstance(fu.instruction, RType_Instruction):
                        fu.result = fu.instruction.execute(fu.Vj, fu.Vk)
                    elif isinstance(fu.instruction, IType_Instruction):
                        if fu.instruction.is_load():  # load second clock cycle
                            val = "{:032b}".format(self.DM.load(fu.A))
                            fu.result = int(val[-fu.instruction.length:], 2)
                        else:
                            fu.result = fu.instruction.execute(fu.Vj)
                    elif isinstance(fu.instruction, SType_Instruction):
                        fu.A = fu.instruction.execute(fu.Vj)
                    elif isinstance(fu.instruction, BType_Instruction):
                        pc = self.Regs.PC.get_value() - 4
                        pc += fu.instruction.execute(fu.Vj, fu.Vk)
                        self.Regs.PC.set_value(pc)


    def write(self):
        for fu in self.RS.get_fus_of_thread(self.thread_id):
            if fu.busy and fu.time_remaining == 0:
                self.IFQ.set_instruction_write_result(fu.instruction.program_counter, self.__steps)
                if isinstance(fu.instruction, SType_Instruction):
                    val = "{:032b}".format(fu.Vk)
                    old = list("{:032b}".format(self.DM.load(fu.A)))

                    for i in range(1, fu.instruction.length):
                        old[-i] = val[-i]

                    self.DM.store(fu.A, int("".join(old), 2))
                elif isinstance(fu.instruction, BType_Instruction):
                    self.stall = False
                else:
                    self.RegisterStat.remove_status(fu.instruction.rd, fu.instruction.rd_type)
                    self.Regs.write(fu.instruction.rd, fu.result, fu.instruction.rd_type)

                    # Write result
                    for other_fu in self.RS:
                        if other_fu.Qj == fu.name:
                            other_fu.Vj = fu.result
                            other_fu.Qj = 0
                        if other_fu.Qk == fu.name:
                            other_fu.Vk = fu.result
                            other_fu.Qk = 0

                fu.clear()


    def is_halted(self):
        return (
            self.IFQ.empty(self.Regs.PC.get_value())
            and self.RS.all_empty()
        )


    def get_steps(self):
        return self.__steps
