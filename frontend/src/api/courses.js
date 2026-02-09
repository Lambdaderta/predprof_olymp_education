// src/api/courses.js
import axiosClient from './axiosClient';

export const coursesApi = {
  // Получить список всех курсов
  getAll: async () => {
    try {
      const response = await axiosClient.get('/courses/');
      return response.data;
    } catch (error) {
      console.error("Fetch courses error:", error);
      return []; 
    }
  },
  
  getById: async (id) => {
    try {
      const response = await axiosClient.get(`/courses/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Fetch course ${id} error:`, error);
      return null;
    }
  },
    submitTask: async (taskId, answer, isCorrect) => {
    try {
      await axiosClient.post(`/courses/tasks/${taskId}/solve`, {
        answer: answer,
        is_correct: isCorrect
      });
      return true;
    } catch (error) {
      console.error("Submit task error:", error);
      return false;
    }
  },
    generateSimilarTask: async (taskId) => {
    try {
      const response = await axiosClient.post(`/courses/tasks/${taskId}/generate-similar`);
      return response.data;
    } catch (error) {
      console.error("Generate similar task error:", error);
      throw error;
    }
  }
};