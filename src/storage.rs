use std::collections::HashMap;

#[derive(Clone)]
pub struct FileMetadata {
    pub file_name: String,
    pub content: String,
    pub size: usize,
}

pub struct FileStorage {
    files: HashMap<String, FileMetadata>,
}

impl FileStorage {
    pub fn new() -> Self {
        Self {
            files: HashMap::new(),
        }
    }

    pub fn store_file(&mut self, file_id: &str, file_name: &str, content: &str) {
        let metadata = FileMetadata {
            file_name: file_name.to_string(),
            content: content.to_string(),
            size: content.len(),
        };

        self.files.insert(file_id.to_string(), metadata);
    }

    pub fn get_file(&self, file_id: &str) -> Option<(String, String)> {
        self.files.get(file_id).map(|metadata| {
            (metadata.file_name.clone(), metadata.content.clone())
        })
    }

    pub fn delete_file(&mut self, file_id: &str) -> bool {
        self.files.remove(file_id).is_some()
    }

}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_store_and_retrieve_file() {
        let mut storage = FileStorage::new();
        let file_id = "test-123";
        let file_name = "test.txt";
        let content = "Hello, World!";

        storage.store_file(file_id, file_name, content);
        
        let retrieved = storage.get_file(file_id);
        assert!(retrieved.is_some());
        
        let (retrieved_name, retrieved_content) = retrieved.unwrap();
        assert_eq!(retrieved_name, file_name);
        assert_eq!(retrieved_content, content);
    }

    #[test]
    fn test_delete_file() {
        let mut storage = FileStorage::new();
        let file_id = "test-123";
        
        storage.store_file(file_id, "test.txt", "content");
        assert!(storage.get_file(file_id).is_some());
        
        assert!(storage.delete_file(file_id));
        assert!(storage.get_file(file_id).is_none());
    }

}
