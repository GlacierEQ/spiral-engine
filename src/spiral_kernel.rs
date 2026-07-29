pub struct SpiralExecutionKernel {
    pub pass_index: usize,
    pub active_pistons: usize,
}

impl SpiralExecutionKernel {
    pub fn new(pistons: usize) -> Self {
        SpiralExecutionKernel {
            pass_index: 0,
            active_pistons: pistons,
        }
    }

    pub fn advance_spiral_pass(&mut self) -> usize {
        self.pass_index += 1;
        self.pass_index
    }
}
