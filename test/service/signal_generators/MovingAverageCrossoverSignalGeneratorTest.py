import pytest

from signal_generators.MovingAverageCrossoverSignalGenerator import MovingAverageCrossoverSignalGenerator


class MovingAverageCrossoverSignalGeneratorTest:
    @pytest.fixture
    def setup_data(self):
        data = 5  # Set up a sample number
        print("\nSetting up resources...")
        yield data  # Provide the data to the test
        # Teardown: Clean up resources (if any) after the test
        print("\nTearing down resources...")

    def test_generate_signal(self, setup_data):
        signal_generator = MovingAverageCrossoverSignalGenerator(setup_data)
        assert True

    def test_iterate_queue(self):
        self.fail()

    def test_iterate(self):
        self.fail()
